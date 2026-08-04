"""SQLite storage for the bot's durable user data and conversation context."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


DATABASE_PATH = Path(__file__).with_name("bot_data.sqlite3")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the local database and all tables required by the bot."""
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_started_at TEXT,
                last_interaction_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cart_items (
                telegram_user_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                service_description TEXT NOT NULL,
                service_price TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
                added_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (telegram_user_id, service_name),
                FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                total_amount TEXT,
                currency TEXT,
                payment_reference TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                service_description TEXT NOT NULL,
                service_price TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dialog_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                telegram_user_id INTEGER,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                include_in_context INTEGER NOT NULL DEFAULT 0 CHECK (include_in_context IN (0, 1)),
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_dialog_messages_context
                ON dialog_messages(chat_id, telegram_user_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_orders_user_status
                ON orders(telegram_user_id, status);
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(dialog_messages)")}
        if "include_in_context" not in columns:
            connection.execute(
                "ALTER TABLE dialog_messages ADD COLUMN include_in_context INTEGER NOT NULL DEFAULT 0 "
                "CHECK (include_in_context IN (0, 1))"
            )


def upsert_user(telegram_user_id: int, username: str | None, full_name: str | None, started: bool = False) -> None:
    now = _utc_now()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO users (telegram_user_id, username, full_name, first_started_at, last_interaction_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                first_started_at = COALESCE(users.first_started_at, excluded.first_started_at),
                last_interaction_at = excluded.last_interaction_at
            """,
            (telegram_user_id, username, full_name, now if started else None, now),
        )


def add_cart_item(telegram_user_id: int, service: dict[str, str]) -> int:
    """Add a service or increment its quantity, returning the resulting quantity."""
    now = _utc_now()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO cart_items (
                telegram_user_id, service_name, service_description, service_price, quantity, added_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(telegram_user_id, service_name) DO UPDATE SET
                service_description = excluded.service_description,
                service_price = excluded.service_price,
                quantity = cart_items.quantity + 1,
                updated_at = excluded.updated_at
            """,
            (telegram_user_id, service["name"], service["description"], service["price"], now, now),
        )
        row = connection.execute(
            "SELECT quantity FROM cart_items WHERE telegram_user_id = ? AND service_name = ?",
            (telegram_user_id, service["name"]),
        ).fetchone()
    return int(row["quantity"])


def get_cart_items(telegram_user_id: int) -> list[dict[str, str | int]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT service_name, service_description, service_price, quantity
            FROM cart_items WHERE telegram_user_id = ? ORDER BY added_at, service_name
            """,
            (telegram_user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_draft_order_from_cart(telegram_user_id: int) -> int | None:
    """Snapshot the current cart into an unpaid draft order for a future checkout flow."""
    now = _utc_now()
    with _connection() as connection:
        cart_items = connection.execute(
            """
            SELECT service_name, service_description, service_price, quantity
            FROM cart_items WHERE telegram_user_id = ? ORDER BY added_at, service_name
            """,
            (telegram_user_id,),
        ).fetchall()
        if not cart_items:
            return None

        cursor = connection.execute(
            """
            INSERT INTO orders (telegram_user_id, status, created_at, updated_at)
            VALUES (?, 'draft', ?, ?)
            """,
            (telegram_user_id, now, now),
        )
        order_id = int(cursor.lastrowid)
        connection.executemany(
            """
            INSERT INTO order_items (order_id, service_name, service_description, service_price, quantity)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (order_id, item["service_name"], item["service_description"], item["service_price"], item["quantity"])
                for item in cart_items
            ],
        )
    return order_id


def update_order_status(order_id: int, status: str, payment_reference: str | None = None) -> None:
    """Update an order state without committing to a specific payment provider."""
    with _connection() as connection:
        connection.execute(
            """
            UPDATE orders SET status = ?, payment_reference = ?, updated_at = ? WHERE id = ?
            """,
            (status, payment_reference, _utc_now(), order_id),
        )


def add_dialog_message(
    chat_id: int, telegram_user_id: int | None, role: str, content: str, include_in_context: bool = False
) -> None:
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO dialog_messages (chat_id, telegram_user_id, role, content, include_in_context, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, telegram_user_id, role, content, include_in_context, _utc_now()),
        )


def get_dialog_history(chat_id: int, telegram_user_id: int | None, limit: int) -> list[dict[str, str]]:
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content FROM dialog_messages
                WHERE chat_id = ? AND telegram_user_id IS ? AND include_in_context = 1
                ORDER BY id DESC LIMIT ?
            ) ORDER BY id ASC
            """,
            (chat_id, telegram_user_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def clear_dialog_history(chat_id: int, telegram_user_id: int | None) -> None:
    with _connection() as connection:
        connection.execute(
            "DELETE FROM dialog_messages WHERE chat_id = ? AND telegram_user_id IS ?",
            (chat_id, telegram_user_id),
        )
