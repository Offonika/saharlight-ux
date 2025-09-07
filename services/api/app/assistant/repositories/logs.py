from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from services.api.app.config import settings
from services.api.app.diabetes.services.db import SessionLocal, run_db
from services.api.app.assistant.models import LessonLog
from services.api.app.diabetes.handlers.reminder_jobs import DefaultJobQueue

logger = logging.getLogger(__name__)

__all__ = [
    "add_lesson_log",
    "get_lesson_logs",
    "cleanup_lesson_logs",
    "schedule_lesson_logs_cleanup",
]


async def add_lesson_log(
    user_id: int,
    plan_id: int,
    module_idx: int,
    step_idx: int,
    role: str,
    content: str,
) -> None:
    """Persist a lesson log entry if logging is enabled."""

    if not settings.lesson_logs_enabled:
        return

    def _add(session: Session) -> None:
        session.add(
            LessonLog(
                user_id=user_id,
                plan_id=plan_id,
                module_idx=module_idx,
                step_idx=step_idx,
                role=role,
                content=content,
            )
        )
        session.commit()

    await run_db(_add, sessionmaker=SessionLocal)


async def get_lesson_logs(user_id: int, plan_id: int) -> list[LessonLog]:
    """Return lesson logs for a user and plan ordered by insertion."""

    def _get(session: Session) -> list[LessonLog]:
        return (
            session.query(LessonLog)
            .filter_by(user_id=user_id, plan_id=plan_id)
            .order_by(LessonLog.id)
            .all()
        )

    return await run_db(_get, sessionmaker=SessionLocal)


async def cleanup_lesson_logs(max_age_days: int = 14) -> int:
    """Remove log entries older than ``max_age_days`` days.

    Returns the number of deleted rows.
    """

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    def _cleanup(session: Session) -> int:
        res = (
            session.query(LessonLog)
            .filter(LessonLog.created_at < cutoff)
            .delete()
        )
        session.commit()
        return res

    return await run_db(_cleanup, sessionmaker=SessionLocal)


async def _cleanup_job(_context: object, *, max_age_days: int) -> None:
    try:
        removed = await cleanup_lesson_logs(max_age_days)
        logger.info("lesson_logs cleanup removed %s rows", removed)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("lesson_logs cleanup failed")


def schedule_lesson_logs_cleanup(
    jq: DefaultJobQueue, *, interval: timedelta = timedelta(hours=24), max_age_days: int = 14
) -> None:
    """Schedule periodic cleanup of old lesson logs."""

    run_rep = getattr(jq, "run_repeating", None)
    if not callable(run_rep):
        return
    job_name = "lesson_logs_cleanup"
    run_rep(
        _cleanup_job,
        interval=interval,
        first=interval,
        name=job_name,
        job_kwargs={"id": job_name, "replace_existing": True, "max_age_days": max_age_days},
    )
