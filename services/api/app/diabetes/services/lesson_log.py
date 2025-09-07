from __future__ import annotations

from sqlalchemy.orm import Session

from ..models_learning import LessonLog
from .db import SessionLocal, run_db
from .repository import commit

__all__ = ["add_lesson_log", "get_lesson_logs"]


async def add_lesson_log(
    telegram_id: int,
    topic_slug: str,
    role: str,
    step_idx: int,
    content: str,
) -> None:
    """Insert a lesson log entry."""

    def _add(session: Session) -> None:
        session.add(
            LessonLog(
                telegram_id=telegram_id,
                topic_slug=topic_slug,
                role=role,
                step_idx=step_idx,
                content=content,
            )
        )
        commit(session)

    await run_db(_add, sessionmaker=SessionLocal)


async def get_lesson_logs(telegram_id: int, topic_slug: str) -> list[LessonLog]:
    """Fetch lesson logs for a user and topic."""

    def _get(session: Session) -> list[LessonLog]:
        return (
            session.query(LessonLog)
            .filter_by(telegram_id=telegram_id, topic_slug=topic_slug)
            .order_by(LessonLog.id)
            .all()
        )

    return await run_db(_get, sessionmaker=SessionLocal)
