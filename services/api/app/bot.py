# bot.py
"""
Bot entry point and configuration.
"""

from diabetes.handlers.common_handlers import register_handlers
from backend.services import init_db
from backend.config import LOG_LEVEL, TELEGRAM_TOKEN
from telegram import BotCommand
from telegram.ext import Application, ContextTypes
from sqlalchemy.exc import SQLAlchemyError
import logging
import os
import sys

logger = logging.getLogger(__name__)

MAINTAINER_CHAT_ID = os.getenv("MAINTAINER_CHAT_ID")
try:
    MAINTAINER_CHAT_ID = (
        int(MAINTAINER_CHAT_ID) if MAINTAINER_CHAT_ID is not None else None
    )
except (TypeError, ValueError):
    logger.warning("Invalid MAINTAINER_CHAT_ID: %s", MAINTAINER_CHAT_ID)
    MAINTAINER_CHAT_ID = None


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and optionally notify maintainers."""
    logger.exception(
        "Exception while handling update %s", update, exc_info=context.error
    )
    if MAINTAINER_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=MAINTAINER_CHAT_ID, text=f"⚠️ Exception: {context.error}"
            )
        except Exception:  # pragma: no cover - logging only
            logger.exception("Failed to notify maintainer")

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

    try:
        init_db()
    except (SQLAlchemyError, ValueError) as err:
        logger.exception("Failed to initialize the database: %s", err)
        sys.exit(
            "Database initialization failed. Please check your configuration and try again."
        )

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
