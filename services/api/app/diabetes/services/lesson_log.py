from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from ...config import settings
from ..models_learning import LessonLog
from .db import SessionLocal, run_db
from .repository import commit

logger = logging.getLogger(__name__)

__all__ = [
    "add_lesson_log",
    "get_lesson_logs",
    "flush_pending_logs",
    "start_flush_task",
]


@dataclass(slots=True)
class _PendingLog:
    telegram_id: int
    topic_slug: str
    role: str
    step_idx: int
    content: str


pending_logs: list[_PendingLog] = []
_flush_task: asyncio.Task[None] | None = None
_FLUSH_INTERVAL = 5.0


async def flush_pending_logs() -> None:
    """Flush accumulated logs to the database."""

    if not pending_logs:
        return

    entries = [LessonLog(**asdict(log)) for log in pending_logs]

    def _flush(session: Session) -> None:
        session.add_all(entries)
        commit(session)

    try:
        await run_db(_flush, sessionmaker=SessionLocal)
    except Exception:  # pragma: no cover - logging only
        logger.exception("Failed to flush %s lesson logs", len(entries))
        return

    pending_logs.clear()


async def add_lesson_log(
    telegram_id: int,
    topic_slug: str,
    role: str,
    step_idx: int,
    content: str,
) -> None:
    """Queue a lesson log entry and attempt to flush."""

    if not settings.learning_logging_required:
        return

    pending_logs.append(
        _PendingLog(
        telegram_id=telegram_id,
        topic_slug=topic_slug,
        role=role,
        step_idx=step_idx,
        content=content,
        )
    )

    await flush_pending_logs()


async def _flush_periodically(interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        await flush_pending_logs()


def start_flush_task(interval: float = _FLUSH_INTERVAL) -> None:
    """Start background task that periodically flushes logs."""

    global _flush_task
    if _flush_task is None or _flush_task.done():
        _flush_task = asyncio.create_task(_flush_periodically(interval))


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
