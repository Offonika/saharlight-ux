from __future__ import annotations

from typing import cast
from datetime import datetime

from sqlalchemy.orm import Session

from ...assistant.models import AssistantMemory
from ...diabetes.services.db import SessionLocal, run_db
from ...diabetes.services.repository import commit
from ...types import SessionProtocol


async def get_memory(user_id: int) -> str | None:
    """Return stored memory summary for ``user_id`` if present."""

    def _get(session: SessionProtocol) -> str | None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        return None if record is None else record.summary_text

    return await run_db(_get, sessionmaker=SessionLocal)


async def save_memory(user_id: int, memory: str) -> None:
    """Persist ``memory`` for ``user_id`` overwriting existing value."""

    def _save(session: SessionProtocol) -> None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        now = datetime.utcnow()
        if record is None:
            record = AssistantMemory(
                user_id=user_id,
                summary_text=memory,
                turn_count=0,
                last_turn_at=now,
            )
            cast(Session, session).add(record)
        else:
            record.summary_text = memory
            record.turn_count = 0
            record.last_turn_at = now
        commit(cast(Session, session))

    await run_db(_save, sessionmaker=SessionLocal)


async def clear_memory(user_id: int) -> None:
    """Remove stored memory for ``user_id`` if present."""

    def _clear(session: SessionProtocol) -> None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        if record is None:
            return
        session.delete(record)
        commit(cast(Session, session))

    await run_db(_clear, sessionmaker=SessionLocal)


__all__ = ["AssistantMemory", "get_memory", "save_memory", "clear_memory"]
