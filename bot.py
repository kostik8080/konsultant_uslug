import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters


MENU_TEXTS = {
    "experience": (
        "Опыт\n\n"
        "Я помогаю потенциальным клиентам быстро понять, чем специалист может быть полезен: "
        "рассказываю об опыте, подходе к работе, реализованных проектах и формате сотрудничества.\n\n"
        "Каркас можно дополнить конкретными фактами: годы опыта, отрасли, стек, ключевые достижения."
    ),
    "projects": (
        "Проекты\n\n"
        "Здесь можно показать 3-5 сильных кейсов: задачу клиента, решение, результат и ссылку на портфолио.\n\n"
        "Пример структуры кейса: проблема -> что сделали -> измеримый результат -> чем это полезно новому клиенту."
    ),
    "services": (
        "Услуги\n\n"
        "- Консультация и разбор задачи.\n"
        "- Проектирование решения.\n"
        "- Разработка Telegram-ботов и автоматизаций.\n"
        "- Доработка существующих проектов.\n\n"
        "Список услуг и цены лучше уточнить под реальное предложение владельца."
    ),
    "contacts": (
        "Контакты и заявка\n\n"
        "Напишите коротко, что нужно сделать, какой срок и как с вами связаться. "
        "Бот подскажет, какие данные лучше отправить владельцу."
    ),
}


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Опыт", callback_data="experience"), InlineKeyboardButton("Проекты", callback_data="projects")],
            [InlineKeyboardButton("Услуги", callback_data="services"), InlineKeyboardButton("Контакты / заявка", callback_data="contacts")],
        ]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact_url = os.getenv("CONTACT_URL", "")
    contact_hint = f"\n\nПрямая связь: {contact_url}" if contact_url else ""
    text = (
        "Здравствуйте! Я бот-консультант по портфолио и услугам.\n\n"
        "Помогу быстро узнать об опыте, проектах, услугах и оставить заявку. "
        "Выберите раздел ниже или напишите вопрос сообщением."
        f"{contact_hint}"
    )
    await update.message.reply_text(text, reply_markup=main_menu())


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = MENU_TEXTS.get(query.data, "Раздел не найден. Попробуйте выбрать пункт меню еще раз.")
    await query.edit_message_text(text=text, reply_markup=main_menu())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start — открыть меню бота\n"
        "/help — показать помощь\n\n"
        "Также можно написать вопрос обычным сообщением."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Спасибо за сообщение. В текущем каркасе я умею показывать основные разделы через /start.\n\n"
        "Для заявки напишите: какая задача, желаемый срок, бюджет или ориентир, контакт для связи."
    )


def build_application() -> Application:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN. Создайте .env по примеру .env.example или задайте переменную окружения.")

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(menu_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application


def main() -> None:
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
