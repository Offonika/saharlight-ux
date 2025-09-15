"""In-memory queue and persistence for lesson logs.

Logs are accumulated in :data:`pending_logs` and periodically flushed to the
database.  To prevent unbounded memory growth, the queue size is limited by
``PENDING_LOG_LIMIT`` which defaults to the ``PENDING_LOG_LIMIT`` environment
variable.  When the limit is exceeded the oldest entries are discarded.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.api.app.config import settings
from services.api.app.assistant.models import LessonLog
from services.api.app.diabetes.metrics import lesson_log_failures, pending_logs_size
from services.api.app.diabetes.services.db import SessionLocal, run_db, User
from services.api.app.diabetes.services.monitoring import notify
from services.api.app.diabetes.services.repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = [
    "add_lesson_log",
    "get_lesson_logs",
    "flush_pending_logs",
    "start_flush_task",
    "start_flush_task_async",
    "stop_flush_task",
    "cleanup_old_logs",
    "safe_add_lesson_log",
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
PENDING_LOG_LIMIT = settings.pending_log_limit
_flush_task: asyncio.Task[None] | None = None
_FLUSH_INTERVAL = 5.0


def _trim_pending_logs() -> None:
    """Ensure ``pending_logs`` does not exceed :data:`PENDING_LOG_LIMIT`."""
    if len(pending_logs) > PENDING_LOG_LIMIT:
        del pending_logs[:-PENDING_LOG_LIMIT]
    pending_logs_size.set(len(pending_logs))


async def flush_pending_logs() -> None:
    """Flush accumulated logs to the database."""
    async with pending_logs_lock:
        if not pending_logs:
            pending_logs_size.set(0)
            return

        queued = pending_logs.copy()
        pending_logs.clear()
        pending_logs_size.set(0)

    def _flush(session: Session) -> list[_PendingLog]:
        missing: list[_PendingLog] = []
        to_insert: list[LessonLog] = []
        for log in queued:
            if session.get(User, log.user_id) is None:
                missing.append(log)
                continue
            to_insert.append(LessonLog(**asdict(log)))
        if to_insert:
            session.add_all(to_insert)
            commit(session)
        return missing

    try:
        missing = await run_db(_flush, sessionmaker=SessionLocal)
    except CommitError as exc:
        if isinstance(exc.__cause__, IntegrityError):
            missing = []
        else:  # pragma: no cover - logging only
            lesson_log_failures.inc(len(queued))
            async with pending_logs_lock:
                pending_logs.extend(queued)
                _trim_pending_logs()
            if settings.learning_logging_required:
                raise
            return
    except Exception as exc:  # pragma: no cover - logging only
        lesson_log_failures.inc(len(queued))
        async with pending_logs_lock:
            pending_logs.extend(queued)
            _trim_pending_logs()
        logger.exception("flush_pending_logs failed", exc_info=exc)
        if settings.learning_logging_required:
            raise
        return

    if missing:
        async with pending_logs_lock:
            pending_logs.extend(missing)
            _trim_pending_logs()


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
        _trim_pending_logs()

    await flush_pending_logs()


async def safe_add_lesson_log(
    user_id: int,
    plan_id: int,
    module_idx: int,
    step_idx: int,
    role: str,
    content: str,
) -> bool:
    """Safely queue and flush a lesson log entry.

    The log is first constructed so it can be re-queued on failure.  The
    existing :func:`add_lesson_log` is invoked to perform the actual
    enqueue and flush.  ``True`` is returned if the log was successfully
    flushed to the database, otherwise ``False``.

    When an exception occurs the log is kept in ``pending_logs`` without
    duplication, the ``lesson_log_failures`` metric is incremented and a
    warning is emitted.  If ``learning_logging_required`` is enabled, the
    error is escalated via an error log and Sentry notification but the
    function still returns ``False`` so callers can proceed.
    """

    log = _PendingLog(
        user_id=user_id,
        plan_id=plan_id,
        module_idx=module_idx,
        step_idx=step_idx,
        role=role,
        content=content,
    )

    try:
        await add_lesson_log(user_id, plan_id, module_idx, step_idx, role, content)
    except Exception as exc:  # pragma: no cover - defensive
        async with pending_logs_lock:
            if log not in pending_logs:
                pending_logs.append(log)
                _trim_pending_logs()
        lesson_log_failures.inc()
        logger.warning("Failed to add lesson log: %s", asdict(log), exc_info=exc)
        if settings.learning_logging_required:
            logger.error("Failed to add lesson log", exc_info=exc)
            notify("lesson_log_failure")
        return False

    async with pending_logs_lock:
        flushed = log not in pending_logs
    return flushed


async def _flush_periodically(interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await flush_pending_logs()
        except Exception as exc:  # pragma: no cover - logging only
            logger.exception("Failed to flush pending logs", exc_info=exc)


def start_flush_task(interval: float = _FLUSH_INTERVAL) -> None:
    """Start background task that periodically flushes logs."""

    global _flush_task
    if _flush_task is not None and not _flush_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.info("No running event loop, skipping flush task start")
        return
    _flush_task = loop.create_task(_flush_periodically(interval))

    def _on_done(task: asyncio.Task[None]) -> None:
        global _flush_task
        exc: BaseException | None = None
        try:
            exc = task.exception()
        except asyncio.CancelledError:  # pragma: no cover - expected
            pass
        if exc is not None:
            logger.exception("Background flush task failed", exc_info=exc)
            _flush_task = None
            start_flush_task(interval)
        else:
            _flush_task = None

    _flush_task.add_done_callback(_on_done)


async def start_flush_task_async(interval: float = _FLUSH_INTERVAL) -> None:
    """Explicit API to start flush task from an async context."""

    start_flush_task(interval)


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
