from __future__ import annotations

import datetime
import logging
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram.ext import ContextTypes, JobQueue

from services.api.app.diabetes.services.db import Reminder, User

logger = logging.getLogger(__name__)

DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]


def schedule_reminder(
    rem: Reminder, job_queue: DefaultJobQueue | None, user: User | None
) -> None:
    """Schedule a reminder in the provided job queue."""
    if job_queue is None:
        logger.warning("schedule_reminder called without job_queue")
        return

    # Import lazily to avoid circular imports.
    from services.api.app import reminder_events
    from . import reminder_handlers

    reminder_events.set_job_queue(job_queue)
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

    tz: datetime.tzinfo = timezone.utc
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
        except (OSError, ValueError) as exc:
            logger.exception("Unexpected error loading timezone %s: %s", tzname, exc)

    if rem.type == "after_meal":
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
            job_queue.run_once(
                reminder_job,
                when=timedelta(minutes=float(minutes_after)),
                data={"reminder_id": rem.id, "chat_id": rem.telegram_id},
                name=name,
            )
    else:
        if rem.time:
            logger.debug(
                "Adding job for reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
                rem.id,
                rem.type,
                rem.time,
                rem.interval_hours or rem.interval_minutes,
                rem.minutes_after,
            )
            job_queue.run_daily(
                reminder_job,
                time=rem.time.replace(tzinfo=tz),
                data={"reminder_id": rem.id, "chat_id": rem.telegram_id},
                name=name,
            )
        elif rem.interval_hours or rem.interval_minutes:
            logger.debug(
                "Adding job for reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
                rem.id,
                rem.type,
                rem.time,
                rem.interval_hours or rem.interval_minutes,
                rem.minutes_after,
            )
            minutes = (
                rem.interval_hours * 60
                if rem.interval_hours is not None
                else rem.interval_minutes or 0
            )
            job_queue.run_repeating(
                reminder_job,
                interval=timedelta(minutes=minutes),
                data={"reminder_id": rem.id, "chat_id": rem.telegram_id},
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
