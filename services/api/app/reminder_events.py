from __future__ import annotations

import logging

from telegram.ext import ContextTypes, JobQueue

from sqlalchemy.orm import Session, sessionmaker

from .diabetes.services.db import Reminder, User
from .diabetes.handlers.reminder_jobs import DefaultJobQueue, schedule_reminder

logger = logging.getLogger(__name__)

_job_queue: DefaultJobQueue | None = None
SessionLocal: sessionmaker[Session] | None = None


def set_job_queue(job_queue: JobQueue[ContextTypes.DEFAULT_TYPE] | None) -> None:
    """Register a shared JobQueue used to schedule reminders."""
    global _job_queue
    _job_queue = job_queue


def notify_reminder_saved(reminder_id: int) -> None:
    """Send reminder to the job queue for scheduling.

    If the job queue is not configured, this function logs a warning and
    returns without scheduling.
    """
    jq = _job_queue
    if jq is None:
        logger.warning("notify_reminder_saved called without job_queue")
        return

    from .diabetes.handlers import reminder_handlers

    session_factory = SessionLocal or reminder_handlers.SessionLocal
    with session_factory() as session:
        rem = session.get(Reminder, reminder_id)
        user = session.get(User, rem.telegram_id) if rem is not None else None
    if rem is None:
        logger.warning("Reminder %s not found for scheduling", reminder_id)
        return
    schedule_reminder(rem, jq, user)


__all__ = ["set_job_queue", "notify_reminder_saved"]
