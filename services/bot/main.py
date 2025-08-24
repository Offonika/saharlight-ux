# main.py
"""
Bot entry point and configuration.
"""

import asyncio
import logging
import sys
from typing import Any

from telegram.ext import Application, ContextTypes, ExtBot, JobQueue
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.diabetes.services.db import init_db

from services.api.app.config import settings
from services.bot.configure_commands import configure_commands

DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]
logger = logging.getLogger(__name__)


TELEGRAM_TOKEN = settings.telegram_token


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
    ] = Application.builder().token(BOT_TOKEN).build()

    asyncio.run(configure_commands(application))
    application.add_error_handler(error_handler)

    from services.api.app.diabetes.handlers.registration import register_handlers

    register_handlers(application)
    application.run_polling()


__all__ = ["main", "error_handler", "settings", "TELEGRAM_TOKEN"]


if __name__ == "__main__":
    main()
