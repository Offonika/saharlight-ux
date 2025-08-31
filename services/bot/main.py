"""
Bot entry point and configuration.
"""

import logging
import sys

from sqlalchemy.exc import SQLAlchemyError
from telegram import BotCommand
from telegram.ext import Application, ContextTypes, ExtBot, JobQueue

from services.api.app.config import settings
from services.api.app.diabetes.services.db import init_db
from services.api.app.menu_button import post_init as menu_button_post_init

DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = settings.telegram_token

commands = [
    BotCommand("start", "🚀 Запустить бота"),
    BotCommand("menu", "📋 Главное меню"),
    BotCommand("profile", "👤 Мой профиль"),
    BotCommand("report", "📊 Отчёт"),
    BotCommand("history", "📚 История записей"),
    BotCommand("sugar", "🩸 Расчёт сахара"),
    BotCommand("gpt", "🤖 Чат с GPT"),
    BotCommand("reminders", "⏰ Список напоминаний"),
    BotCommand("help", "❓ Справка"),
]


async def post_init(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        DefaultJobQueue,
    ],
) -> None:
    await app.bot.set_my_commands(commands)
    await menu_button_post_init(app)

    # 🟢 Проверка, что JobQueue инициализирован
    job_queue = getattr(app, "job_queue", None)
    if job_queue:
        logger.info("✅ JobQueue initialized and ready")
    else:
        logger.error("❌ JobQueue is NOT available!")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors that occur while processing updates."""
    logger.exception(
        "Exception while handling update %s", update, exc_info=context.error
    )


def main() -> None:  # pragma: no cover
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
        sys.exit(
            "Database initialization failed. Please check your configuration and try again."
        )

    BOT_TOKEN = TELEGRAM_TOKEN
    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN is not set. Please provide the environment variable.",
        )
        sys.exit(1)

    application: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
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

    # 🟢 Тестовая задача (через 30 секунд после запуска)
    async def test_job(context: ContextTypes.DEFAULT_TYPE) -> None:
        await context.bot.send_message(
            chat_id=settings.admin_id,
            text="🔔 Test reminder fired! JobQueue работает ✅",
        )

    if application.job_queue:
        application.job_queue.run_once(test_job, when=30)

    application.run_polling()

__all__ = ["main", "error_handler", "settings", "TELEGRAM_TOKEN"]


if __name__ == "__main__":  # pragma: no cover
    main()

