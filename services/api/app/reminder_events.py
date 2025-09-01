from __future__ import annotations

import logging

import asyncio
from typing import Callable, cast

from sqlalchemy.orm import Session, sessionmaker

from .diabetes.services.db import Reminder, User
from .diabetes.handlers.reminder_jobs import DefaultJobQueue, schedule_reminder

logger = logging.getLogger(__name__)

# Shared job queue used across the application. It is configured during
# application startup via :func:`register_job_queue`.
job_queue: DefaultJobQueue | None = None
SessionLocal: sessionmaker[Session] | None = None


def register_job_queue(jq: DefaultJobQueue | None) -> None:
    """Register a shared JobQueue used to schedule reminders."""
    global job_queue
    job_queue = jq


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

    Raises RuntimeError if the job queue is not configured.
    """
    jq = job_queue
    if jq is None:
        msg = "notify_reminder_deleted called without job_queue"
        raise RuntimeError(msg)
    removed = 0
    for job in jq.get_jobs_by_name(f"reminder_{reminder_id}"):
        remover = cast(Callable[[], None] | None, getattr(job, "remove", None))
        if remover is not None:
            try:
                remover()
                removed += 1
                continue
            except Exception:  # pragma: no cover - defensive
                pass
        scheduler = getattr(jq, "scheduler", None)
        remove_job = (
            cast(Callable[[object], None] | None, getattr(scheduler, "remove_job", None))
            if scheduler is not None
            else None
        )
        job_id = getattr(job, "id", None)
        if remove_job is not None and job_id is not None:
            try:
                remove_job(job_id)
                removed += 1
                continue
            except Exception:  # pragma: no cover - defensive
                pass
        schedule_removal = cast(
            Callable[[], None] | None, getattr(job, "schedule_removal", None)
        )
        if schedule_removal is not None:
            schedule_removal()
            removed += 1
    logger.info("Removed %d job(s) for reminder %s", removed, reminder_id)


__all__ = ["register_job_queue", "notify_reminder_saved", "notify_reminder_deleted"]
