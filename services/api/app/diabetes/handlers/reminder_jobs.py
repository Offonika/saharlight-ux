from __future__ import annotations

import logging
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, TypeAlias
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram.ext import ContextTypes, JobQueue

from services.api.app.diabetes.services.db import Reminder, User
from services.api.app.diabetes.utils.jobs import schedule_once

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
        logger.debug(
            "Reminder %s disabled, skipping (type=%s, time=%s, interval=%s, minutes_after=%s)",
            rem.id,
            rem.type,
            rem.time,
            rem.interval_hours or rem.interval_minutes,
            rem.minutes_after,
        )
        return

    if user is None:
        with SessionLocal() as session:
            user = session.get(User, rem.telegram_id)

    tzname = getattr(user, "timezone", None) if user else None
    try:
        tz = ZoneInfo(tzname or "UTC")
    except ZoneInfoNotFoundError:
        logger.warning("Invalid timezone for user %s: %s", getattr(user, "telegram_id", None), tzname)
        tz = ZoneInfo("UTC")

    name = f"reminder_{rem.id}"
    kind = rem.kind
    if kind is None:
        if rem.minutes_after is not None:
            kind = "after_event"
        elif rem.interval_hours or rem.interval_minutes:
            kind = "every"
        else:
            kind = "at_time"

    logger.info(
        "PLAN %s kind=%s time=%s interval_min=%s after_min=%s tz=%s",
        rem.id,
        kind,
        rem.time,
        rem.interval_minutes or (rem.interval_hours or 0) * 60,
        rem.minutes_after,
        tz,
    )

    data = {"reminder_id": rem.id, "chat_id": rem.telegram_id}
    context = SimpleNamespace(job=SimpleNamespace(data=data))

    if kind == "after_event" and rem.minutes_after is not None:
        schedule_once(
            job_queue,
            reminder_job,
            when=timedelta(minutes=float(rem.minutes_after)),
            data=data,
            name=name,
            timezone=tz,
        )
    elif rem.time is not None:
        params = {
            "trigger": "cron",
            "id": name,
            "name": name,
            "replace_existing": True,
            "hour": rem.time.hour,
            "minute": rem.time.minute,
            "timezone": tz,
            "kwargs": {"context": context},
        }
        mask = getattr(rem, "days_mask", 0) or 0
        if mask:
            params["day_of_week"] = ",".join(str(i) for i in range(7) if mask & (1 << i))
        job_queue.scheduler.add_job(reminder_job, **params)
    else:
        minutes = rem.interval_minutes or (rem.interval_hours or 0) * 60
        if minutes:
            job_queue.scheduler.add_job(
                reminder_job,
                trigger="interval",
                id=name,
                name=name,
                replace_existing=True,
                minutes=int(minutes),
                timezone=tz,
                kwargs={"context": context},
            )


__all__ = ["DefaultJobQueue", "schedule_reminder"]
