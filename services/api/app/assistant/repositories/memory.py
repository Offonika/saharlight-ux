from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from services.api.app.assistant.models import AssistantMemory
from services.api.app.diabetes.services.repository import commit

__all__ = ["get_memory", "upsert_memory"]


def get_memory(session: Session, user_id: int) -> AssistantMemory | None:
    """Return stored memory for a user if present."""
    return session.get(AssistantMemory, user_id)


def upsert_memory(
    session: Session,
    *,
    user_id: int,
    turn_count: int,
    last_turn_at: datetime,
) -> AssistantMemory:
    """Insert or update conversation memory for a user."""
    memory = session.get(AssistantMemory, user_id)
    if memory is None:
        memory = AssistantMemory(
            user_id=user_id,
            turn_count=turn_count,
            last_turn_at=last_turn_at,
        )
        session.add(memory)
    else:
        memory.turn_count = turn_count
        memory.last_turn_at = last_turn_at
    commit(session)
    return memory
