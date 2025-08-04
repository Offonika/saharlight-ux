# bot.py

from diabetes.common_handlers import register_handlers
from diabetes.db import init_db
from diabetes.config import LOG_LEVEL, TELEGRAM_TOKEN
from telegram import BotCommand
from telegram.ext import Application
from sqlalchemy.exc import SQLAlchemyError
import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


async def main() -> None:
    """Configure and start the bot."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("=== Bot started ===")

    BOT_TOKEN = TELEGRAM_TOKEN
    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN is not set. Please provide the environment variable."
        )
        sys.exit(1)

    try:
        init_db()
    except SQLAlchemyError:
        logger.exception("Failed to initialize the database")
        sys.exit(1)

    application = Application.builder().token(BOT_TOKEN).build()
    register_handlers(application)

    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("menu", "Главное меню"),
        BotCommand("profile", "Мой профиль"),
        BotCommand("report", "Отчёт"),
        BotCommand("sugar", "Расчёт сахара"),
        BotCommand("gpt", "Чат с GPT"),
        BotCommand("reminders", "Список напоминаний"),
        BotCommand("addreminder", "Добавить напоминание"),
        BotCommand("delreminder", "Удалить напоминание"),
        BotCommand("help", "Справка"),
    ]
    await application.bot.set_my_commands(commands)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
