from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ...diabetes.services.db import SessionLocal, run_db
from ...diabetes.services.repository import commit
from ..models import AssistantMemory
from ..repositories.memory import (
    get_memory as repo_get_memory,
    upsert_memory as repo_upsert_memory,
)

__all__ = [
    "AssistantMemory",
    "get_memory",
    "save_memory",
    "clear_memory",
    "record_turn",
    "cleanup_old_memory",
]


async def get_memory(user_id: int) -> AssistantMemory | None:
    """Return stored memory for ``user_id`` if present."""

    def _get(session: Session) -> AssistantMemory | None:
        return repo_get_memory(session, user_id)

    return await run_db(_get, sessionmaker=SessionLocal)


async def save_memory(
    user_id: int,
    *,
    turn_count: int,
    last_turn_at: datetime,
    summary_text: str = "",
) -> AssistantMemory:
    """Persist conversation metadata for ``user_id``."""

    summary_text = summary_text[:1024]

    def _save(session: Session) -> AssistantMemory:
        return repo_upsert_memory(
            session,
            user_id=user_id,
            turn_count=turn_count,
            last_turn_at=last_turn_at,
            summary_text=summary_text,
        )

    return await run_db(_save, sessionmaker=SessionLocal)


async def clear_memory(user_id: int) -> None:
    """Remove stored memory for ``user_id`` if present."""

    def _clear(session: Session) -> None:
        record = repo_get_memory(session, user_id)
        if record is None:
            return
        session.delete(record)
        commit(session)

    await run_db(_clear, sessionmaker=SessionLocal)


async def record_turn(
    user_id: int,
    *,
    summary_text: str | None = None,
    now: datetime | None = None,
) -> None:
    """Increment turn count for ``user_id`` and optionally update summary."""

    if now is None:
        now = datetime.now(timezone.utc)

    if summary_text is not None:
        summary_text = summary_text[:1024]

    def _save(session: Session) -> None:
        existing = repo_get_memory(session, user_id)
        prev_count = 0 if existing is None else existing.turn_count
        repo_upsert_memory(
            session,
            user_id=user_id,
            turn_count=prev_count + 1,
            last_turn_at=now,
            summary_text=summary_text,
        )

    await run_db(_save, sessionmaker=SessionLocal)


async def cleanup_old_memory(ttl: timedelta | None = None) -> None:
    """Delete assistant memory entries older than ``ttl``."""

    from services.api.app.config import settings

    days = settings.assistant_memory_ttl_days
    ttl = ttl or timedelta(days=days)
    cutoff = datetime.now(timezone.utc) - ttl

    def _cleanup(session: Session) -> int:
        deleted = (
            session.query(AssistantMemory)
            .where(AssistantMemory.last_turn_at < cutoff)
            .delete(synchronize_session=False)
        )
        commit(session)
        return deleted

    await run_db(_cleanup, sessionmaker=SessionLocal)
