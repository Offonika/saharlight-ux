# main.py
"""
Bot entry point and configuration.
"""

import logging
import sys

from telegram import BotCommand
from telegram.ext import Application, ContextTypes
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.services import init_db

from services.api.app.config import LOG_LEVEL, settings
from services.api.app.diabetes.handlers.common_handlers import register_handlers

logger = logging.getLogger(__name__)


TELEGRAM_TOKEN = settings.telegram_token


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors that occur while processing updates."""
    logger.exception(
        "Exception while handling update %s", update, exc_info=context.error
    )

def main() -> None:
    """Configure and run the bot."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("=== Bot started ===")

    try:
        init_db()
    except SQLAlchemyError as exc:
        logger.error("Failed to initialize the database", exc_info=exc)
        sys.exit("Database initialization failed. Please check your configuration and try again.")

    BOT_TOKEN = TELEGRAM_TOKEN
    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN is not set. Please provide the environment variable.",
        )
        sys.exit(1)

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
    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands(commands)

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)  # registers post-init handler
        .build()
    )
    application.add_error_handler(error_handler)
    register_handlers(application)
    application.run_polling()

if __name__ == "__main__":
    main()
