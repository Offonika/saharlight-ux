# file: services/bot/main.py
"""Bot entry point and configuration."""

import logging
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from telegram import BotCommand
from telegram.ext import (
    Application,
    ContextTypes,
    ExtBot,
    JobQueue,
    PicklePersistence,
)

from services.api.app.billing.jobs import schedule_subscription_expiration
from services.api.app.config import settings
from services.api.app.diabetes.handlers.registration import register_handlers
from services.api.app.diabetes.services.db import init_db
from services.api.app.menu_button import post_init as menu_button_post_init
from services.bot.handlers.start_webapp import build_start_handler
from services.bot.ptb_patches import apply_jobqueue_stop_workaround  # 👈 добавили
from services.bot.telegram_payments import register_billing_handlers

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
    BotCommand("trial", "🎁 Trial"),
    BotCommand("upgrade", "💳 Оформить PRO"),
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
    if app.job_queue:
        logger.info("✅ JobQueue initialized and ready")
    else:
        logger.error("❌ JobQueue is NOT available!")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception(
        "Exception while handling update %s", update, exc_info=context.error
    )


def build_persistence() -> (
    PicklePersistence[dict[str, object], dict[str, object], dict[str, object]]
):
    """Create PicklePersistence with configurable path.

    Path can be overridden via ``BOT_PERSISTENCE_PATH``. By default it is stored
    in ``data/state`` within the repository. The base directory can be
    overridden via ``STATE_DIRECTORY``. The directory is created if it does not
    exist and must be writable.
    """

    default_state_dir = Path(__file__).resolve().parents[2] / "data/state"
    state_dir_str = os.environ.get("STATE_DIRECTORY")
    state_dir = Path(state_dir_str) if state_dir_str else default_state_dir
    state_dir.mkdir(parents=True, exist_ok=True)
    default_path = state_dir / "bot_persistence.pkl"
    persistence_path_str = os.environ.get("BOT_PERSISTENCE_PATH")
    persistence_path = (
        Path(persistence_path_str) if persistence_path_str else default_path
    )
    persistence_path.parent.mkdir(parents=True, exist_ok=True)
    if not os.access(persistence_path.parent, os.W_OK):
        raise RuntimeError(
            f"Persistence directory is not writable: {persistence_path.parent}"
        )
    return PicklePersistence(str(persistence_path), single_file=True)


def main() -> None:  # pragma: no cover
    level = settings.log_level
    if isinstance(level, str):  # pragma: no cover - runtime config
        level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.info("=== Bot started ===")

    # применяем воркараунд к PTB JobQueue.stop
    apply_jobqueue_stop_workaround()

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
        logger.error("BOT_TOKEN is not set. Please provide the environment variable.")
        sys.exit(1)

    # ---- Build application
    try:
        persistence = build_persistence()
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error(
            "Failed to initialize persistence. "
            "Ensure STATE_DIRECTORY points to a writable directory.",
            exc_info=exc,
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
        .persistence(persistence)
        .post_init(post_init)
        .build()
    )

    application.add_handler(build_start_handler(), group=0)
    logger.info("✅ /start → WebApp CTA mode enabled")

    # ---- Configure APScheduler timezone BEFORE any scheduling
    tz_msk = ZoneInfo("Europe/Moscow")
    job_queue = application.job_queue
    if job_queue is None:
        raise RuntimeError("JobQueue not initialized")
    job_queue.scheduler.configure(timezone=tz_msk)
    logger.info("✅ JobQueue timezone set to %s", job_queue.scheduler.timezone)

    application.add_error_handler(error_handler)

    # ---- Wire job_queue to API layer
    from services.api.app import reminder_events

    reminder_events.register_job_queue(job_queue)
    reminder_events.schedule_reminders_gc(job_queue)
    schedule_subscription_expiration(job_queue)

    # ---- Register handlers (they may schedule reminders)
    register_handlers(application)
    if settings.learning_mode_enabled:
        logger.info("📚 🤖 Ассистент_AI включён")
    else:
        logger.info("📚 🤖 Ассистент_AI выключен")
    register_billing_handlers(application)

    # ---- Schedule test job on startup
    async def test_job(context: ContextTypes.DEFAULT_TYPE) -> None:
        admin_id = settings.admin_id
        if admin_id is None:
            logger.warning("Admin ID not configured; skipping test reminder")
            return
        await context.bot.send_message(
            chat_id=admin_id, text="🔔 Test reminder fired! JobQueue работает ✅"
        )

    job_queue.run_once(test_job, when=timedelta(seconds=30), name="test_job")
    logger.info("🧪 Scheduled test_job in +30s")

    # ---- Run (без дополнительного ручного shutdown — PTB сделает сам)
    application.run_polling()


__all__ = ["main", "error_handler", "settings", "TELEGRAM_TOKEN", "build_persistence"]

if __name__ == "__main__":  # pragma: no cover
    main()
