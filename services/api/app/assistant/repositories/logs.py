from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.api.app.config import settings
from services.api.app.assistant.models import LessonLog
from services.api.app.diabetes.metrics import lesson_log_failures
from services.api.app.diabetes.services.db import SessionLocal, run_db, User
from services.api.app.diabetes.services.repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = [
    "add_lesson_log",
    "get_lesson_logs",
    "flush_pending_logs",
    "start_flush_task",
    "stop_flush_task",
    "cleanup_old_logs",
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
pending_logs_lock = asyncio.Lock()
_flush_task: asyncio.Task[None] | None = None
_FLUSH_INTERVAL = 5.0


async def flush_pending_logs() -> None:
    """Flush accumulated logs to the database."""
    async with pending_logs_lock:
        if not pending_logs:
            return

        queued = pending_logs.copy()
        pending_logs.clear()

    def _flush(session: Session) -> list[_PendingLog]:
        missing: list[_PendingLog] = []
        for log in queued:
            if session.get(User, log.user_id) is None:
                missing.append(log)
                continue
            session.add(LessonLog(**asdict(log)))
            try:
                commit(session)
            except CommitError as exc:
                if isinstance(exc.__cause__, IntegrityError):
                    continue
                raise
        return missing

    try:
        missing = await run_db(_flush, sessionmaker=SessionLocal)
    except Exception as exc:  # pragma: no cover - logging only
        logger.warning("Failed to flush %s lesson logs", len(queued), exc_info=exc)
        lesson_log_failures.inc(len(queued))
        if settings.learning_logging_required:
            raise
        async with pending_logs_lock:
            pending_logs.extend(queued)
        return

    if missing:
        async with pending_logs_lock:
            pending_logs.extend(missing)


async def add_lesson_log(
    user_id: int,
    plan_id: int,
    module_idx: int,
    step_idx: int,
    role: str,
    content: str,
) -> None:
    """Queue a lesson log entry and attempt to flush."""
    async with pending_logs_lock:
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


async def stop_flush_task() -> None:
    """Cancel the background flush task if it's running."""

    global _flush_task
    task = _flush_task
    if task is None:
        return
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:  # pragma: no cover - expected
            pass
    _flush_task = None


async def get_lesson_logs(user_id: int, plan_id: int) -> list[LessonLog]:
    """Fetch lesson logs for a user and plan."""

    def _get(session: Session) -> list[LessonLog]:
        return (
            session.query(LessonLog)
            .filter(LessonLog.user_id == user_id, LessonLog.plan_id == plan_id)
            .order_by(LessonLog.id)
            .all()
        )

    return await run_db(_get, sessionmaker=SessionLocal)


async def cleanup_old_logs(ttl: timedelta | None = None) -> None:
    """Remove lesson logs older than ``ttl``."""

    days = settings.lesson_logs_ttl_days
    ttl = ttl or timedelta(days=days)
    cutoff = datetime.now(timezone.utc) - ttl

    def _cleanup(session: Session) -> int:
        query = session.query(LessonLog).where(LessonLog.created_at < cutoff)
        deleted = query.delete(synchronize_session=False)
        commit(session)
        return deleted

    removed = await run_db(_cleanup, sessionmaker=SessionLocal)
    if removed:
        logger.info("Removed %s stale lesson log(s)", removed)
