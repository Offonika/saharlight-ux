from __future__ import annotations

from datetime import datetime, timezone
from typing import MutableMapping, cast

from sqlalchemy.orm import Session

from ...diabetes import assistant_state
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
]


async def get_memory(user_id: int) -> AssistantMemory | None:
    """Return stored memory for ``user_id`` if present."""

    def _get(session: Session) -> AssistantMemory | None:
        return repo_get_memory(session, user_id)

    return await run_db(_get, sessionmaker=SessionLocal)


async def save_memory(
    user_id: int, *, summary_text: str, turn_count: int, last_turn_at: datetime
) -> AssistantMemory:
    """Persist ``summary_text`` for ``user_id`` overwriting existing value."""

    def _save(session: Session) -> AssistantMemory:
        return repo_upsert_memory(
            session,
            user_id=user_id,
            summary_text=summary_text,
            turn_count=turn_count,
            last_turn_at=last_turn_at,
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
    user_data: MutableMapping[str, object],
    text: str,
    *,
    now: datetime | None = None,
) -> None:
    """Record assistant reply and persist summary if threshold exceeded."""

    summarized = assistant_state.add_turn(user_data, text)
    if summarized == 0:
        return
    if now is None:
        now = datetime.now(timezone.utc)

    summary = cast(str, user_data[assistant_state.SUMMARY_KEY])

    def _save(session: Session) -> None:
        existing = repo_get_memory(session, user_id)
        prev_count = 0 if existing is None else existing.turn_count
        repo_upsert_memory(
            session,
            user_id=user_id,
            summary_text=summary,
            turn_count=prev_count + summarized,
            last_turn_at=now,
        )

    await run_db(_save, sessionmaker=SessionLocal)
