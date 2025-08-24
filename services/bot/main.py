# main.py
"""
Bot entry point and configuration.
"""

import logging
import os
import sys
from typing import Any, cast

from telegram import BotCommand, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, ContextTypes, ExtBot, JobQueue
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.diabetes.services.db import init_db

from services.api.app.config import settings

DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]
logger = logging.getLogger(__name__)


TELEGRAM_TOKEN = settings.telegram_token

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


async def post_init(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        DefaultJobQueue,
    ],
) -> None:
    await app.bot.set_my_commands(commands)
    webapp_url = os.getenv("WEBAPP_URL")
    if not webapp_url:
        logger.warning("WEBAPP_URL not configured, skip ChatMenuButton")
        return

    menu = [
        MenuButtonWebApp("⏰", WebAppInfo(url=f"{webapp_url}/reminders")),
        MenuButtonWebApp("📊", WebAppInfo(url=f"{webapp_url}/history")),
        MenuButtonWebApp("📄", WebAppInfo(url=f"{webapp_url}/profile")),
        MenuButtonWebApp("💳", WebAppInfo(url=f"{webapp_url}/subscription")),
    ]
    await app.bot.set_chat_menu_button(menu_button=cast(Any, menu))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors that occur while processing updates."""
    logger.exception("Exception while handling update %s", update, exc_info=context.error)


def main() -> None:
    """Configure and run the bot."""
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("=== Bot started ===")

    try:
        init_db()
    except ValueError as exc:
        logger.error("Invalid database configuration", exc_info=exc)
        sys.exit("Invalid configuration. Please check your settings and try again.")
    except SQLAlchemyError as exc:
        logger.error("Failed to initialize the database", exc_info=exc)
        sys.exit("Database initialization failed. Please check your configuration and try again.")

    BOT_TOKEN = TELEGRAM_TOKEN
    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN is not set. Please provide the environment variable.",
        )
        sys.exit(1)

    application: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        DefaultJobQueue,
    ] = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)  # registers post-init handler
        .build()
    )
    application.add_error_handler(error_handler)

    from services.api.app.diabetes.handlers.registration import register_handlers

    register_handlers(application)
    application.run_polling()


__all__ = ["main", "error_handler", "settings", "TELEGRAM_TOKEN"]


if __name__ == "__main__":
    main()
