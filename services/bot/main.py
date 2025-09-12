# file: services/bot/main.py
"""Bot entry point and configuration."""

import os
from pathlib import Path
from types import ModuleType, SimpleNamespace

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[2] / "data/mpl-cache"),
)

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, TypeAlias, cast
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from telegram import BotCommand
from telegram.error import NetworkError, RetryAfter
from telegram.ext import (
    Application,
    ContextTypes,
    ExtBot,
    JobQueue,
    PicklePersistence,
)

import config
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

redis_stub = SimpleNamespace()
redis_stub.Redis = SimpleNamespace(from_url=lambda *a, **k: None)
redis_stub.from_url = lambda *a, **k: redis_stub.Redis.from_url(*a, **k)
redis: ModuleType | SimpleNamespace = redis_stub

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
    global redis
    if not isinstance(redis, ModuleType):
        try:
            import redis.asyncio as real_redis  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            logger.warning(
                "Redis package not installed; command caching disabled"
            )
        else:
            patched_from_url = getattr(redis.Redis, "from_url", None)
            if patched_from_url is not None:
                real_redis.Redis.from_url = patched_from_url
            redis = real_redis

    redis_client: Any | None = None
    should_set = True
    try:
        redis_raw = redis.from_url(settings.redis_url)  # type: ignore[no-untyped-call]
        redis_client = cast(Any, redis_raw)
        raw_ts = await redis_client.get("bot:commands_set_at")
        if raw_ts:
            last_set = datetime.fromisoformat(raw_ts.decode())
            if datetime.now(timezone.utc) - last_set < timedelta(hours=24):
                should_set = False
    except Exception as exc:  # pragma: no cover - network/cache issues
        logger.warning("Redis unavailable: %s", exc)

    if should_set:
        try:
            await app.bot.set_my_commands(commands)
        except RetryAfter as exc:
            logger.warning("Flood control: retrying in %ss", exc.retry_after)
            await asyncio.sleep(exc.retry_after)
            try:
                await app.bot.set_my_commands(commands)
            except (RetryAfter, NetworkError):
                logger.warning("Flood control: unable to set commands")
        if redis_client is not None:
            try:
                await redis_client.set(
                    "bot:commands_set_at",
                    datetime.now(timezone.utc).isoformat(),
                    ex=int(timedelta(hours=25).total_seconds()),
                )
            except Exception as exc:  # pragma: no cover - network/cache issues
                logger.warning("Failed to store commands timestamp: %s", exc)
    else:
        logger.info("Skipping set_my_commands; recently updated")
    if redis_client is not None:
        await redis_client.close()
    await menu_button_post_init(app)
    from services.api.app.diabetes.handlers import assistant_menu

    await assistant_menu.post_init(app)
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

    try:
        config.validate_tokens(["TELEGRAM_TOKEN", "OPENAI_API_KEY"])
    except RuntimeError as exc:
        logger.error("Environment validation failed: %s", exc)
        sys.exit(1)

    BOT_TOKEN = cast(str, TELEGRAM_TOKEN)

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
