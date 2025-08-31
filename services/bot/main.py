"""
Bot entry point and configuration.
"""

import logging
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from telegram import BotCommand
from telegram.ext import Application, ContextTypes, ExtBot, JobQueue
from typing import TYPE_CHECKING, TypeAlias

from services.api.app.config import settings
from services.api.app.diabetes.services.db import init_db
from services.api.app.menu_button import post_init as menu_button_post_init

if TYPE_CHECKING:
    DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    DefaultJobQueue = JobQueue
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
    if app.job_queue:
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

    builder = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)  # registers post-init handler
    )
    timezone = ZoneInfo("Europe/Moscow")
    if hasattr(builder, "timezone"):
        builder = builder.timezone(timezone)
    elif hasattr(builder, "job_queue"):
        builder = builder.job_queue(DefaultJobQueue())
    application: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        DefaultJobQueue,
    ] = builder.build()
    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError("JobQueue not initialized")
    job_queue.scheduler.configure(timezone=timezone)
    logger.info(
        "✅ JobQueue initialized with timezone %s",
        job_queue.scheduler.timezone,
    )
    application.add_error_handler(error_handler)

    from services.api.app import reminder_events

    reminder_events.set_job_queue(job_queue)

    from services.api.app.diabetes.handlers.registration import register_handlers

    register_handlers(application)

    # 🟢 Тестовая задача (через 30 секунд после запуска)
    async def test_job(context: ContextTypes.DEFAULT_TYPE) -> None:
        admin_id = settings.admin_id
        if admin_id is None:  # pragma: no cover - misconfiguration
            logger.warning("Admin ID not configured; skipping test reminder")
            return
        await context.bot.send_message(
            chat_id=admin_id,
            text="🔔 Test reminder fired! JobQueue работает ✅",
        )

    if job_queue:
        tzinfo = (
            job_queue.scheduler.timezone
            if job_queue.scheduler.timezone
            else ZoneInfo("UTC")
        )
        when = datetime.now(tz=tzinfo) + timedelta(seconds=30)
        job_queue.run_once(
            test_job,
            when=when,
        )

    try:
        application.run_polling()
    finally:
        if getattr(job_queue.scheduler, "running", False):
            job_queue.scheduler.shutdown()


__all__ = ["main", "error_handler", "settings", "TELEGRAM_TOKEN"]


if __name__ == "__main__":  # pragma: no cover
    main()
