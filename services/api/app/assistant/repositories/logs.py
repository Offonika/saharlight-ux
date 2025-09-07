from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from services.api.app.config import settings
from services.api.app.diabetes.models_learning import LessonLog
from services.api.app.diabetes.services.db import SessionLocal, run_db
from services.api.app.diabetes.services.repository import commit

logger = logging.getLogger(__name__)

__all__ = [
    "add_lesson_log",
    "get_lesson_logs",
    "flush_pending_logs",
    "start_flush_task",
    "cleanup_lesson_logs",
    "pending_logs",
]


@dataclass(slots=True)
class _PendingLog:
    user_id: int
    plan_id: int
    module_idx: int
    step_idx: int
    role: str
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
    user_id: int,
    plan_id: int,
    module_idx: int,
    step_idx: int,
    role: str,
    content: str,
) -> None:
    """Queue a lesson log entry and attempt to flush."""

    if not settings.learning_logging_required:
        return

    pending_logs.append(
        _PendingLog(
            user_id=user_id,
            plan_id=plan_id,
            module_idx=module_idx,
            step_idx=step_idx,
            role=role,
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


async def get_lesson_logs(user_id: int, plan_id: int, module_idx: int) -> list[LessonLog]:
    """Fetch lesson logs for a user, plan and module."""

    def _get(session: Session) -> list[LessonLog]:
        return (
            session.query(LessonLog)
            .filter_by(user_id=user_id, plan_id=plan_id, module_idx=module_idx)
            .order_by(LessonLog.id)
            .all()
        )

    return await run_db(_get, sessionmaker=SessionLocal)


async def cleanup_lesson_logs(max_age_days: int = 14) -> None:
    """Remove lesson logs older than ``max_age_days`` days."""

    threshold = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)

    def _cleanup(session: Session) -> None:
        session.query(LessonLog).filter(LessonLog.created_at < threshold).delete()
        commit(session)

    try:
        await run_db(_cleanup, sessionmaker=SessionLocal)
    except Exception:  # pragma: no cover - logging only
        logger.exception("Failed to cleanup lesson logs")
