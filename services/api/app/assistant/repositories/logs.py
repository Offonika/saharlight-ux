from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import cast

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ...config import settings
from ...diabetes.models_learning import LessonLog
from ...diabetes.services.db import SessionLocal, run_db
from ...diabetes.services.repository import commit
from ...types import SessionProtocol

logger = logging.getLogger(__name__)

__all__ = ["add_lesson_log", "get_lesson_logs", "cleanup_lesson_logs"]


async def add_lesson_log(
    user_id: int,
    plan_id: int,
    module_idx: int,
    step_idx: int,
    role: str,
    content: str,
) -> None:
    """Insert a lesson log entry."""

    if not settings.learning_logging_required:
        return

    def _add(session: SessionProtocol) -> None:
        sess = cast(Session, session)
        sess.add(
            LessonLog(
                user_id=user_id,
                plan_id=plan_id,
                module_idx=module_idx,
                step_idx=step_idx,
                role=role,
                content=content,
            )
        )
        commit(sess)

    try:
        await run_db(_add, sessionmaker=SessionLocal)
    except Exception:  # pragma: no cover - logging only
        logger.exception("Failed to add lesson log for %s", user_id)


async def get_lesson_logs(user_id: int, plan_id: int) -> list[LessonLog]:
    """Fetch lesson logs for a user and plan."""

    def _get(session: SessionProtocol) -> list[LessonLog]:
        sess = cast(Session, session)
        stmt = (
            sa.select(LessonLog)
            .where(LessonLog.user_id == user_id, LessonLog.plan_id == plan_id)
            .order_by(LessonLog.id)
        )
        return list(sess.scalars(stmt).all())

    return await run_db(_get, sessionmaker=SessionLocal)


async def cleanup_lesson_logs(max_age_days: int = 14) -> int:
    """Delete lesson logs older than ``max_age_days`` days.

    Returns the number of rows removed.
    """

    def _cleanup(session: SessionProtocol) -> int:
        threshold = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        sess = cast(Session, session)
        stmt = sa.delete(LessonLog).where(LessonLog.created_at < threshold)
        result = sess.execute(stmt)
        commit(sess)
        return int(result.rowcount or 0)

    return await run_db(_cleanup, sessionmaker=SessionLocal)
