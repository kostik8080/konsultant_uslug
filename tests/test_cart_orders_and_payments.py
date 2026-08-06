import asyncio
from types import SimpleNamespace

import bot
import database


USER_ID = 101
SERVICE = {"name": "Telegram-бот", "description": "Разработка бота", "price": "1 500 ₽"}


def add_user() -> None:
    database.upsert_user(USER_ID, "test_user", "Тестовый пользователь", started=True)


def create_order() -> dict[str, object]:
    add_user()
    database.add_cart_item(USER_ID, SERVICE)
    order = database.checkout_cart(USER_ID)
    assert order is not None
    return order


def test_cart_add_remove_total_and_duplicate_service(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "bot.sqlite3")
    database.initialize_database()
    add_user()

    assert database.add_cart_item(USER_ID, SERVICE) == 1
    assert database.add_cart_item(USER_ID, SERVICE) == 2
    items = database.get_cart_items(USER_ID)

    assert len(items) == 1
    assert items[0]["quantity"] == 2
    text, _ = bot.cart_text_and_keyboard(items)
    assert "Итого: 3 000 ₽" in text

    assert database.remove_cart_item(USER_ID, str(items[0]["token"])) is True
    assert database.get_cart_items(USER_ID)[0]["quantity"] == 1
    assert database.remove_cart_item(USER_ID, str(items[0]["token"])) is True
    assert database.get_cart_items(USER_ID) == []
    assert database.remove_cart_item(USER_ID, str(items[0]["token"])) is False


def test_checkout_creates_order_clears_cart_and_rejects_empty_cart(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "bot.sqlite3")
    database.initialize_database()

    order = create_order()

    assert order["total_amount"] == 1500
    assert database.get_cart_items(USER_ID) == []
    stored_order = database.get_order(int(order["id"]), USER_ID)
    assert stored_order is not None
    assert stored_order["status"] == "ожидает оплаты"
    assert database.checkout_cart(USER_ID) is None


def test_database_data_persists_after_reopening_connection(tmp_path, monkeypatch):
    database_path = tmp_path / "persistent.sqlite3"
    monkeypatch.setattr(database, "DATABASE_PATH", database_path)
    database.initialize_database()
    add_user()
    database.add_cart_item(USER_ID, SERVICE)

    # Each public operation opens and closes its own SQLite connection.
    assert database_path.exists()
    assert database.get_cart_items(USER_ID) == [
        {
            "service_name": "Telegram-бот",
            "service_description": "Разработка бота",
            "service_price": "1 500 ₽",
            "quantity": 1,
            "token": database._cart_item_token("Telegram-бот"),
        }
    ]


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class FakeQuery:
    def __init__(self, order_id: int):
        self.data = f"{bot.CHECK_PAYMENT_CALLBACK_PREFIX}{order_id}"
        self.message = FakeMessage()
        self.answers = []

    async def answer(self, text=None):
        self.answers.append(text)


class FakeStripeResponse:
    def __init__(self, payment_status: str):
        self.payment_status = payment_status

    def raise_for_status(self):
        pass

    def json(self):
        return {"payment_status": self.payment_status}


class FakeStripeClient:
    payment_status = "unpaid"
    requested_urls = []

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, url, **kwargs):
        self.requested_urls.append(url)
        return FakeStripeResponse(self.payment_status)


def test_payment_marks_order_paid_only_after_confirmed_stripe_payment(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "bot.sqlite3")
    monkeypatch.setattr(bot, "get_order", database.get_order)
    monkeypatch.setattr(bot, "mark_order_paid", database.mark_order_paid)
    monkeypatch.setattr(bot.httpx, "AsyncClient", FakeStripeClient)
    monkeypatch.setenv("SCRIPE_KEY", "sk_test_fake")
    database.initialize_database()
    order = create_order()
    order_id = int(order["id"])
    database.save_payment_session(order_id, "cs_test_123", "https://example.test/checkout")
    update = SimpleNamespace(
        callback_query=FakeQuery(order_id),
        effective_user=SimpleNamespace(id=USER_ID, full_name="Тест", username="test_user"),
    )
    context = SimpleNamespace(bot=SimpleNamespace(send_message=None))

    FakeStripeClient.payment_status = "unpaid"
    asyncio.run(bot.check_payment_callback(update, context))
    assert database.get_order(order_id, USER_ID)["status"] == "ожидает оплаты"

    FakeStripeClient.payment_status = "paid"
    asyncio.run(bot.check_payment_callback(update, context))
    assert database.get_order(order_id, USER_ID)["status"] == "оплачен"
    assert FakeStripeClient.requested_urls == [
        f"{bot.STRIPE_API_URL}/cs_test_123",
        f"{bot.STRIPE_API_URL}/cs_test_123",
    ]
