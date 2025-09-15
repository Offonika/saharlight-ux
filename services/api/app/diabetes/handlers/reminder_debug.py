# services/api/app/diabetes/handlers/reminder_debug.py
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from services.api.app.config import settings
from services.api.app.diabetes.utils.jobs import dbg_jobs_dump


logger = logging.getLogger(__name__)


def _is_admin(update: Update) -> bool:
    user = update.effective_user
    return bool(user and settings.admin_id and user.id == settings.admin_id)


def _fmt_jobs(app: Application) -> str:
    """Форматирует список джобов из APScheduler."""
    tz = app.job_queue.scheduler.timezone
    jobs = app.job_queue.scheduler.get_jobs()  # type: ignore[attr-defined]
    if not jobs:
        return "📭 Джобов нет"

    lines: list[str] = []
    for j in jobs:
        nrt = j.next_run_time  # aware dt or None
        if nrt is None:
            when_msk = when_utc = "—"
        else:
            when_utc = nrt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            when_msk = nrt.astimezone(tz).strftime(
                f"%Y-%m-%d %H:%M:%S {tz.key if hasattr(tz,'key') else 'TZ'}"
            )
        job_text = "\n".join(
            [
                f"• {j.name}  (id={j.id})",
                f"  next_run: {when_msk} | {when_utc}",
                f"  trigger: {j.trigger!s}",
            ]
        )
        lines.append(job_text)
    return "📋 Запланированные задачи:\n" + "\n".join(lines)


async def dbg_tz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    tz = context.application.job_queue.scheduler.timezone
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    now_msk = datetime.now(ZoneInfo("Europe/Moscow")).strftime(
        "%Y-%m-%d %H:%M:%S Europe/Moscow"
    )
    await update.effective_chat.send_message(
        f"🧭 TZ в планировщике: {tz}\n"
        f"⏱️ now(UTC): {now_utc}\n"
        f"⏱️ now(MSK): {now_msk}"
    )


async def dbg_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    dump = dbg_jobs_dump(context.application.job_queue)
    logger.debug("dbg_jobs_dump: %s", dump)
    text = _fmt_jobs(context.application)
    await update.effective_chat.send_message(text)


async def dbg_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    await update.effective_chat.send_message("🏓 Пинг! Отправка сообщений работает ✅")


async def dbg_enqueue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /dbg_enqueue 10  — поставить разовую задачу на +N секунд, которая пришлёт сообщение сюда.
    """
    if not _is_admin(update):
        return
    try:
        secs = int(context.args[0]) if context.args else 10
        secs = max(1, min(secs, 3600))
    except ValueError:
        secs = 10

    async def _job(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔔 DEBUG job отстрелил через +{secs}s ✅",
        )

    context.application.job_queue.run_once(_job, when=secs, name=f"debug_echo_{secs}s")
    await update.effective_chat.send_message(f"🧪 Поставил debug-джоб на +{secs}s")


def register_debug_reminder_handlers(app: Application) -> None:
    """
    Регистрируем только для админа и только если включены DEBUG-команды.
    """
    from os import getenv

    if getenv("ENABLE_DEBUG_COMMANDS", "0") != "1":
        return

    app.add_handler(CommandHandler("dbg_tz", dbg_tz))
    app.add_handler(CommandHandler("dbg_jobs", dbg_jobs))
    app.add_handler(CommandHandler("dbg_ping", dbg_ping))
    app.add_handler(CommandHandler("dbg_enqueue", dbg_enqueue))
