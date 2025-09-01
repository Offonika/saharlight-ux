from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, TypeAlias
from zoneinfo import ZoneInfo

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

    if kind == "after_event" and rem.minutes_after is not None:
        when_td = timedelta(minutes=float(rem.minutes_after))
        schedule_once(
            job_queue,
            reminder_job,
            when=when_td,
            data=context,
            name=name,
            timezone=tz,
            job_kwargs={"id": name, "name": name, "replace_existing": True},
        )
    elif kind == "at_time" and rem.time is not None:
        params: dict[str, object] = {
            "hour": rem.time.hour,
            "minute": rem.time.minute,
        }
        mask = getattr(rem, "days_mask", 0) or 0
        if mask:
            days = ",".join(str(i) for i in range(7) if mask & (1 << i))
            params["day_of_week"] = days
        job_queue.scheduler.add_job(
            reminder_job,
            trigger="cron",
            id=name,
            name=name,
            replace_existing=True,
            timezone=tz,
            kwargs={"context": context},
            **params,
        )
    elif kind == "every" and rem.interval_minutes is not None:
        job_queue.scheduler.add_job(
            reminder_job,
            trigger="interval",
            id=name,
            name=name,
            replace_existing=True,
            minutes=int(rem.interval_minutes),
            timezone=tz,
            kwargs={"context": context},
        )


__all__ = ["DefaultJobQueue", "schedule_reminder"]
