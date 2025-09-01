from __future__ import annotations

import inspect
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any, TypeAlias, cast
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes, JobQueue

from services.api.app.diabetes.services.db import Reminder, User

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    DefaultJobQueue = JobQueue


def schedule_reminder(
    rem: Reminder, job_queue: DefaultJobQueue | None, user: User | None
) -> None:
    if job_queue is None:
        raise RuntimeError("schedule_reminder called without job_queue")
    if rem.telegram_id is None:
        raise ValueError("schedule_reminder called without telegram_id")

    from services.api.app import reminder_events
    from . import reminder_handlers

    reminder_events.register_job_queue(job_queue)
    reminder_job = reminder_handlers.reminder_job
    SessionLocal = reminder_handlers.SessionLocal

    if not rem.is_enabled:
        return

    if user is None:
        with SessionLocal() as session:
            user = session.get(User, rem.telegram_id)
    tz = ZoneInfo(getattr(user, "timezone", None) or "UTC")

    name = f"reminder_{rem.id}"

    # ---- kind detection + back-compat ----
    kind = rem.kind
    if kind is None:
        if rem.minutes_after is not None:
            kind = "after_event"
        elif (rem.interval_minutes is not None) or (rem.interval_hours is not None):
            kind = "every"
        else:
            kind = "at_time"

    # расчёт интервала с back-compat
    interval_min = rem.interval_minutes
    if interval_min is None and rem.interval_hours is not None:
        interval_min = int(rem.interval_hours) * 60

    logger.info(
        "PLAN %s kind=%s time=%s interval_min=%s after_min=%s tz=%s",
        name,
        kind,
        rem.time,
        interval_min,
        rem.minutes_after,
        tz,
    )

    context: dict[str, object] = {"reminder_id": rem.id, "chat_id": rem.telegram_id}
    job_kwargs: dict[str, object] = {"id": name, "name": name, "replace_existing": True}

    if kind == "after_event":
        # ВАЖНО: не планируем заранее. Ставится только при триггере (schedule_after_meal / snooze).
        logger.info("Skip scheduling %s: 'after_event' is scheduled on trigger.", name)
        next_run = None

    elif kind == "at_time" and rem.time is not None:
        mask = getattr(rem, "days_mask", 0) or 0
        days = tuple(i for i in range(7) if mask & (1 << i)) if mask else None

        run_daily = job_queue.run_daily
        sig = inspect.signature(run_daily)
        t = rem.time
        if "timezone" not in sig.parameters:
            # PTB без параметра timezone — делаем time tz-aware
            t = rem.time.replace(tzinfo=tz)

        if days is not None and "days" in sig.parameters:
            cast(Any, run_daily)(
                reminder_job,
                time=t,
                days=days,
                data=context,
                name=name,
                job_kwargs=job_kwargs,
                timezone=tz if "timezone" in sig.parameters else None,
            )
        else:
            cast(Any, run_daily)(
                reminder_job,
                time=t,
                data=context,
                name=name,
                job_kwargs=job_kwargs,
                timezone=tz if "timezone" in sig.parameters else None,
            )

        job = next(iter(job_queue.get_jobs_by_name(name)), None)
        next_run = (
            getattr(job, "next_run_time", None)
            or getattr(job, "next_t", None)
            or getattr(job, "when", None)
            or getattr(job, "run_time", None)
        )

    elif kind == "every" and interval_min and interval_min > 0:
        job_queue.run_repeating(
            reminder_job,
            interval=timedelta(minutes=int(interval_min)),
            data=context,
            name=name,
            job_kwargs=job_kwargs,
        )
        job = next(iter(job_queue.get_jobs_by_name(name)), None)
        next_run = (
            getattr(job, "next_run_time", None)
            or getattr(job, "next_t", None)
            or getattr(job, "when", None)
            or getattr(job, "run_time", None)
        )
    else:
        next_run = None

    logger.info("SET %s kind=%s next_run=%s", name, kind, next_run)


__all__ = ["DefaultJobQueue", "schedule_reminder"]
