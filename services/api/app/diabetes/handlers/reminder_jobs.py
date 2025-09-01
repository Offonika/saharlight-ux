from __future__ import annotations

import inspect
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, TypeAlias
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes, JobQueue

from services.api.app.diabetes.services.db import Reminder, User

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    DefaultJobQueue = JobQueue


def schedule_reminder(rem: Reminder, job_queue: DefaultJobQueue | None, user: User | None) -> None:
    """Schedule a reminder in the provided job queue."""
    if job_queue is None:
        msg = "schedule_reminder called without job_queue"
        raise RuntimeError(msg)
    if rem.telegram_id is None:
        msg = "schedule_reminder called without telegram_id"
        raise ValueError(msg)

    # Import lazily to avoid circular imports.
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
    kind = rem.kind
    if kind is None:
        if rem.minutes_after is not None:
            kind = "after_event"
        elif rem.interval_minutes:
            kind = "every"
        else:
            kind = "at_time"

    logger.info(
        "PLAN %s kind=%s time=%s interval_min=%s after_min=%s tz=%s",
        name,
        kind,
        rem.time,
        rem.interval_minutes,
        rem.minutes_after,
        tz,
    )

    context: dict[str, object] = {"reminder_id": rem.id, "chat_id": rem.telegram_id}

    job_kwargs = {"id": name, "name": name, "replace_existing": True}
    if kind == "after_event":
        logger.info("Skip scheduling %s: 'after_event' is scheduled on trigger.", name)
        return
    elif kind == "at_time" and rem.time is not None:
        mask = getattr(rem, "days_mask", 0) or 0
        days = tuple(i for i in range(7) if mask & (1 << i)) if mask else None
        params = {
            "time": rem.time,
            "data": context,
            "name": name,
            "job_kwargs": job_kwargs,
        }
        sig = inspect.signature(job_queue.run_daily)
        if "timezone" in sig.parameters:
            params["timezone"] = tz
        if days is not None and "days" in sig.parameters:
            params["days"] = days
        job_queue.run_daily(reminder_job, **params)
    elif kind == "every" and rem.interval_minutes is not None:
        job_queue.run_repeating(
            reminder_job,
            interval=timedelta(minutes=int(rem.interval_minutes)),
            data=context,
            name=name,
            job_kwargs=job_kwargs,
        )

    job = next(iter(job_queue.get_jobs_by_name(name)), None)
    next_run = None
    if job is not None:
        next_run = (
            getattr(job, "next_run_time", None)
            or getattr(job, "next_t", None)
            or getattr(job, "when", None)
            or getattr(job, "run_time", None)
        )
    logger.info("SET %s kind=%s next_run=%s", name, kind, next_run)


__all__ = ["DefaultJobQueue", "schedule_reminder"]
