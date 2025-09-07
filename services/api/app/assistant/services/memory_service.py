from __future__ import annotations

from datetime import datetime, timezone
from typing import MutableMapping, cast

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
]


async def get_memory(user_id: int) -> AssistantMemory | None:
    """Return stored memory for ``user_id`` if present."""

    def _get(session: Session) -> AssistantMemory | None:
        return repo_get_memory(session, user_id)

    return await run_db(_get, sessionmaker=SessionLocal)


async def save_memory(
    user_id: int, *, profile_url: str | None, turn_count: int, last_turn_at: datetime
) -> AssistantMemory:
    """Persist profile link and counters for ``user_id``."""

    def _save(session: Session) -> AssistantMemory:
        return repo_upsert_memory(
            session,
            user_id=user_id,
            profile_url=profile_url,
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
    *,
    now: datetime | None = None,
) -> None:
    """Increment turn counter without storing raw text."""

    if now is None:
        now = datetime.now(timezone.utc)

    def _save(session: Session) -> None:
        existing = repo_get_memory(session, user_id)
        prev_count = 0 if existing is None else existing.turn_count
        repo_upsert_memory(
            session,
            user_id=user_id,
            profile_url=cast(str | None, user_data.get("profile_url")),
            turn_count=prev_count + 1,
            last_turn_at=now,
        )

    await run_db(_save, sessionmaker=SessionLocal)
