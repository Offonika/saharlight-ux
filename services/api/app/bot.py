# bot.py
"""
Bot entry point and configuration.
"""

import logging
import os
import sys

from telegram import BotCommand
from telegram.ext import Application, ContextTypes

from services.api.app.config import LOG_LEVEL
from services.api.app.diabetes.handlers.common_handlers import register_handlers

logger = logging.getLogger(__name__)


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


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
