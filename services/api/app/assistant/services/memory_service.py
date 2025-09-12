from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ...diabetes.services.db import SessionLocal, run_db
from ...diabetes.services.repository import commit
from ..models import AssistantMemory, AssistantNote
from ..repositories.memory import (
    get_memory as repo_get_memory,
    upsert_memory as repo_upsert_memory,
)
from ..repositories.notes import create_note

__all__ = [
    "AssistantMemory",
    "AssistantNote",
    "get_memory",
    "save_memory",
    "clear_memory",
    "record_turn",
    "cleanup_old_memory",
    "save_note",
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


async def save_note(user_id: int, text: str) -> AssistantNote:
    """Store a free-form note for ``user_id``."""

    text = text[:4096]

    def _save(session: Session) -> AssistantNote:
        return create_note(session, user_id=user_id, text=text)

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
        values: dict[str, object] = {
            "turn_count": AssistantMemory.turn_count + 1,
            "last_turn_at": now,
        }
        if summary_text is not None:
            values["summary_text"] = summary_text

        stmt = (
            sa.update(AssistantMemory)
            .where(AssistantMemory.user_id == user_id)
            .values(**values)
        )

        result = session.execute(stmt)
        if result.rowcount == 0:
            repo_upsert_memory(
                session,
                user_id=user_id,
                turn_count=1,
                last_turn_at=now,
                summary_text=summary_text,
            )
        else:
            commit(session)

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
