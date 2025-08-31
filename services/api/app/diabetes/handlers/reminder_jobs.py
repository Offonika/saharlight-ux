from __future__ import annotations

import datetime
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, TypeAlias
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram.ext import ContextTypes, JobQueue

from services.api.app.diabetes.services.db import Reminder, User
from services.api.app.diabetes.utils.jobs import schedule_daily, schedule_once

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

    # Import lazily to avoid circular imports.
    from services.api.app import reminder_events
    from . import reminder_handlers

    reminder_events.register_job_queue(job_queue)
    reminder_job = reminder_handlers.reminder_job
    SessionLocal = reminder_handlers.SessionLocal

    name = f"reminder_{rem.id}"
    for job in job_queue.get_jobs_by_name(name):
        job.schedule_removal()
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

    data: dict[str, object] = {
        "reminder_id": rem.id,
        "chat_id": rem.telegram_id,
    }

    tz: datetime.tzinfo = ZoneInfo("Europe/Moscow")
    if user is None:
        with SessionLocal() as session:
            user = session.get(User, rem.telegram_id)
    tzname = getattr(user, "timezone", None) if user else None
    if tzname:
        try:
            tz = ZoneInfo(tzname)
        except ZoneInfoNotFoundError:
            logger.warning(
                "Invalid timezone for user %s: %s",
                getattr(user, "telegram_id", None),
                tzname,
            )
        except Exception as exc:
            logger.warning("Unexpected error loading timezone %s: %s", tzname, exc)

    job_tz = (
        getattr(getattr(job_queue, "application", None), "timezone", None)
        or getattr(
            getattr(getattr(job_queue, "application", None), "scheduler", None),
            "timezone",
            None,
        )
        or getattr(getattr(job_queue, "scheduler", None), "timezone", None)
        or tz
    )

    kind = rem.kind
    if kind is None:
        if rem.minutes_after is not None:
            kind = "after_event"
        elif rem.interval_hours or rem.interval_minutes:
            kind = "every"
        else:
            kind = "at_time"

    if kind == "after_event":
        minutes_after = rem.minutes_after
        if minutes_after is not None:
            logger.debug(
                "Adding job for reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
                rem.id,
                rem.type,
                rem.time,
                rem.interval_hours or rem.interval_minutes,
                minutes_after,
            )
            when_td = timedelta(minutes=float(minutes_after))
            schedule_once(
                job_queue,
                reminder_job,
                when=when_td,
                data=data,
                name=name,
                timezone=job_tz,
            )
    elif kind == "at_time" and rem.time:
        logger.debug(
            "Adding job for reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
            rem.id,
            rem.type,
            rem.time,
            rem.interval_hours or rem.interval_minutes,
            rem.minutes_after,
        )
        job_time = rem.time.replace(tzinfo=tz)
        days: tuple[int, ...] | None = None
        mask = getattr(rem, "days_mask", 0) or 0
        if mask:
            days = tuple(i for i in range(7) if mask & (1 << i))
        schedule_daily(
            job_queue,
            reminder_job,
            time=job_time,
            data=data,
            name=name,
            timezone=job_tz,
            days=days,
        )
    elif kind == "every":
        minutes = rem.interval_minutes if rem.interval_minutes is not None else (rem.interval_hours or 0) * 60
        if minutes:
            logger.debug(
                "Adding job for reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
                rem.id,
                rem.type,
                rem.time,
                rem.interval_hours or rem.interval_minutes,
                rem.minutes_after,
            )
            job_queue.run_repeating(
                reminder_job,
                interval=timedelta(minutes=minutes),
                data=data,
                name=name,
            )
    logger.debug(
        "Finished scheduling reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
        rem.id,
        rem.type,
        rem.time,
        rem.interval_hours or rem.interval_minutes,
        rem.minutes_after,
    )


__all__ = ["DefaultJobQueue", "schedule_reminder"]
