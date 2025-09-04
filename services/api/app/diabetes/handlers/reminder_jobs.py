from __future__ import annotations

import inspect
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, TypeAlias, Any, cast
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes, JobQueue

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.exc import DetachedInstanceError

from services.api.app.diabetes.services.db import Reminder, User
from services.api.app.diabetes.schemas.reminders import ScheduleKind

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    DefaultJobQueue = JobQueue


def schedule_reminder(
    rem: Reminder, job_queue: DefaultJobQueue | None, user: User | None
) -> None:
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

    profile = None
    tz_name: str | None = None
    if user is None:
        with SessionLocal() as session:
            db_user = session.get(User, rem.telegram_id)
            if db_user is not None:
                profile = getattr(db_user, "profile", None)
                tz_name = getattr(profile, "timezone", None)
    else:
        try:
            profile = getattr(user, "profile")
        except DetachedInstanceError:
            profile = None
        tz_name = getattr(profile, "timezone", None)
        if tz_name is None:
            tz_name = getattr(user, "timezone", None)
    tz = ZoneInfo(tz_name or "UTC")

    base_name = f"reminder_{rem.id}"
    kind = rem.kind
    interval_minutes = rem.interval_minutes
    if kind is None:
        if interval_minutes is None and rem.interval_hours is not None:
            interval_minutes = rem.interval_hours * 60
            kind = ScheduleKind.every
        elif rem.minutes_after is not None:
            kind = ScheduleKind.after_event
        elif interval_minutes:
            kind = ScheduleKind.every
        else:
            kind = ScheduleKind.at_time
    assert kind is not None

    name = f"{base_name}_after" if kind is ScheduleKind.after_event else base_name

    logger.info(
        "PLAN %s kind=%s time=%s interval_min=%s after_min=%s tz=%s",
        name,
        kind,
        rem.time,
        interval_minutes,
        rem.minutes_after,
        tz,
    )

    context: dict[str, object] = {"reminder_id": rem.id, "chat_id": rem.telegram_id}

    job_kwargs: dict[str, object] = {
        "id": name,
        "name": name,
        "replace_existing": True,
    }
    call_job_kwargs = dict(job_kwargs)
    call_job_kwargs.pop("name", None)

    if kind is ScheduleKind.after_event:
        logger.info("SKIP %s kind=%s", name, kind)
        return
    if kind is ScheduleKind.at_time and rem.time is not None:
        run_daily_sig = inspect.signature(job_queue.run_daily)
        run_daily_fn = cast(Any, job_queue.run_daily)
        run_daily_kwargs: dict[str, object] = {
            "time": rem.time,
            "data": context,
            "name": name,
            "job_kwargs": call_job_kwargs,
        }

        if "days" in run_daily_sig.parameters:
            mask = getattr(rem, "days_mask", 0) or 0
            days = (
                tuple(i for i in range(7) if mask & (1 << i))
                if mask
                else tuple(range(7))
            )
            run_daily_kwargs["days"] = days

        if "timezone" in run_daily_sig.parameters:
            run_daily_kwargs["timezone"] = tz
        else:
            run_daily_kwargs["time"] = rem.time.replace(tzinfo=tz)

        run_daily_fn(reminder_job, **run_daily_kwargs)
    elif kind == "every" and interval_minutes is not None:
        if interval_minutes <= 0:
            logger.warning(
                "SKIP %s kind=%s interval_min=%s",
                name,
                kind,
                interval_minutes,
            )
            return
        job_queue.run_repeating(
            reminder_job,
            interval=timedelta(minutes=float(interval_minutes)),
            data=context,
            name=name,
            job_kwargs=call_job_kwargs,
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
