from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker, selectinload
from telegram.ext import ContextTypes

from .diabetes.services.db import Reminder, User
from .diabetes.handlers.reminder_jobs import DefaultJobQueue, schedule_reminder
from services.api.app.diabetes.utils.jobs import _remove_jobs, dbg_jobs_dump

logger = logging.getLogger(__name__)

# Shared job queue used across the application. It is configured during
# application startup via :func:`register_job_queue`.
job_queue: DefaultJobQueue | None = None
SessionLocal: sessionmaker[Session] | None = None

_GC_JOB_NAME = "reminders_gc"


async def _reminders_gc(_context: ContextTypes.DEFAULT_TYPE) -> None:
    """Synchronize reminder jobs with the database."""
    jq = job_queue
    if jq is None:
        return

    from .diabetes.handlers import reminder_handlers

    session_factory = SessionLocal or reminder_handlers.SessionLocal

    def load_active() -> list[Reminder]:
        with session_factory() as session:
            return session.scalars(
                sa.select(Reminder)
                .options(selectinload(Reminder.user).selectinload(User.profile))
                .where(Reminder.is_enabled == True)  # noqa: E712
            ).all()

    reminders = await asyncio.to_thread(load_active)
    active_ids = {rem.id for rem in reminders}

    for rem in reminders:
        try:
            schedule_reminder(rem, jq, rem.user)
        except Exception:  # pragma: no cover - defensive programming
            logger.exception("Failed to schedule reminder %s", rem.id)

    for job_id, name in dbg_jobs_dump(jq):
        nm = name or job_id
        if not nm:
            continue
        match = re.match(r"^reminder_(\d+)", nm)
        if match and int(match.group(1)) not in active_ids:
            _remove_jobs(jq, f"reminder_{match.group(1)}")


def register_job_queue(jq: DefaultJobQueue | None) -> None:
    """Register a shared JobQueue used to schedule reminders."""
    global job_queue
    job_queue = jq


def schedule_reminders_gc(jq: DefaultJobQueue) -> None:
    """Schedule the reminder garbage collector."""
    run_rep = getattr(jq, "run_repeating", None)
    if not callable(run_rep):
        return
    job = run_rep(
        _reminders_gc,
        interval=timedelta(seconds=90),
        first=timedelta(seconds=0),
        name=_GC_JOB_NAME,
        job_kwargs={"id": _GC_JOB_NAME, "replace_existing": True},
    )
    next_run = getattr(job, "next_run_time", None)
    logger.info("🧹 scheduled %s -> next_run=%s", _GC_JOB_NAME, next_run)


async def notify_reminder_saved(reminder_id: int) -> None:
    """Send reminder to the job queue for scheduling.

    Performs database access in a thread pool to avoid blocking the event loop.
    This coroutine must be awaited or scheduled via ``asyncio.create_task`` so
    that the reminder is actually enqueued. Raises :class:`RuntimeError` if the
    job queue is not configured.
    """
    jq = job_queue
    if jq is None:
        msg = "notify_reminder_saved called without job_queue"
        raise RuntimeError(msg)

    from .diabetes.handlers import reminder_handlers

    session_factory = SessionLocal or reminder_handlers.SessionLocal

    def load_objects() -> tuple[Reminder | None, User | None]:
        with session_factory() as session:
            rem = session.get(Reminder, reminder_id)
            user = session.get(User, rem.telegram_id) if rem is not None else None
            return rem, user

    rem, user = await asyncio.to_thread(load_objects)
    if rem is None:
        logger.warning("Reminder %s not found for scheduling", reminder_id)
        return
    if not rem.is_enabled or rem.kind == "after_event":
        notify_reminder_deleted(reminder_id)
        return
    schedule_reminder(rem, jq, user)


def notify_reminder_deleted(reminder_id: int) -> None:
    """Remove reminder jobs from the job queue.

    Removes the base reminder job and associated ``_after`` and ``_snooze``
    variants. Raises :class:`RuntimeError` if the job queue is not configured.
    """
    jq = job_queue
    if jq is None:
        msg = "notify_reminder_deleted called without job_queue"
        raise RuntimeError(msg)
    removed = _remove_jobs(jq, f"reminder_{reminder_id}")
    logger.info("Removed %d job(s) for reminder %s", removed, reminder_id)


__all__ = [
    "register_job_queue",
    "schedule_reminders_gc",
    "notify_reminder_saved",
    "notify_reminder_deleted",
]
