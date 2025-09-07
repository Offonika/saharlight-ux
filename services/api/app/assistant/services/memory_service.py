from __future__ import annotations

from typing import cast

from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from ...diabetes.services.db import Base, SessionLocal, run_db
from ...diabetes.services.repository import commit
from ...types import SessionProtocol


class AssistantMemory(Base):
    """Persisted memory summary for assistant conversations."""

    __tablename__ = "assistant_memory"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    memory: Mapped[str] = mapped_column(Text, nullable=False)


async def get_memory(user_id: int) -> str | None:
    """Return stored memory summary for ``user_id`` if present."""

    def _get(session: SessionProtocol) -> str | None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        return None if record is None else record.memory

    return await run_db(_get, sessionmaker=SessionLocal)


async def save_memory(user_id: int, memory: str) -> None:
    """Persist ``memory`` for ``user_id`` overwriting existing value."""

    def _save(session: SessionProtocol) -> None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        if record is None:
            record = AssistantMemory(user_id=user_id, memory=memory)
            cast(Session, session).add(record)
        else:
            record.memory = memory
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
