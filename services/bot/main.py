# file: services/bot/main.py
"""Bot entry point and configuration."""

import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[2] / "data/mpl-cache"),
)

import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, TypeAlias, cast
from zoneinfo import ZoneInfo

import redis.asyncio as redis

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


REDIS_KEY = "bot:commands_set_at"
COMMANDS_TTL = timedelta(hours=24, minutes=5)


async def update_commands_if_needed(bot: ExtBot[None]) -> None:
    """Update bot commands at most once per day.

    Commands are updated only if the last update stored in Redis is older than
    24 hours. After a successful update, the current timestamp is stored with a
    TTL slightly over one day.
    """

    redis_client = cast(
        redis.Redis,
        redis.from_url(settings.redis_url, decode_responses=True),  # type: ignore[no-untyped-call]
    )
    try:
        ts_raw = await redis_client.get(REDIS_KEY)
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw)
            except ValueError:
                ts = None
            if ts and datetime.now(timezone.utc) - ts < timedelta(hours=24):
                logger.info("Bot commands were updated recently; skipping")
                return

        await bot.set_my_commands(commands)
        await redis_client.set(
            REDIS_KEY,
            datetime.now(timezone.utc).isoformat(),
            ex=COMMANDS_TTL,
        )
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.warning("Redis unavailable, setting commands without cache", exc_info=exc)
        await bot.set_my_commands(commands)
    finally:
        await redis_client.close()


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
    await update_commands_if_needed(app.bot)
    await menu_button_post_init(app)
    from services.api.app.diabetes.handlers import assistant_menu

    await assistant_menu.post_init(app)
    if app.job_queue:
        logger.info("✅ JobQueue initialized and ready")
    else:
        logger.error("❌ JobQueue is NOT available!")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Exception while handling update %s", update, exc_info=context.error)


def build_persistence() -> PicklePersistence[dict[str, object], dict[str, object], dict[str, object]]:
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
    persistence_path = Path(persistence_path_str) if persistence_path_str else default_path
    persistence_path.parent.mkdir(parents=True, exist_ok=True)
    if not os.access(persistence_path.parent, os.W_OK):
        raise RuntimeError(f"Persistence directory is not writable: {persistence_path.parent}")
    return PicklePersistence(str(persistence_path), single_file=True)


def main() -> None:  # pragma: no cover
    level = settings.log_level
    if isinstance(level, str):  # pragma: no cover - runtime config
        level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
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
        sys.exit("Database initialization failed. Please check your configuration and try again.")

    BOT_TOKEN = TELEGRAM_TOKEN
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Please provide the environment variable.")
        sys.exit(1)

    # ---- Build application
    try:
        persistence = build_persistence()
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error(
            "Failed to initialize persistence. Ensure STATE_DIRECTORY points to a writable directory.",
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
    ] = Application.builder().token(BOT_TOKEN).persistence(persistence).post_init(post_init).build()

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
        await context.bot.send_message(chat_id=admin_id, text="🔔 Test reminder fired! JobQueue работает ✅")

    job_queue.run_once(test_job, when=timedelta(seconds=30), name="test_job")
    logger.info("🧪 Scheduled test_job in +30s")

    # ---- Run (без дополнительного ручного shutdown — PTB сделает сам)
    application.run_polling()


__all__ = [
    "main",
    "error_handler",
    "settings",
    "TELEGRAM_TOKEN",
    "build_persistence",
    "update_commands_if_needed",
]

if __name__ == "__main__":  # pragma: no cover
    main()
