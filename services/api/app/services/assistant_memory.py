from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import cast

from sqlalchemy import BigInteger, Text, TIMESTAMP, func, ForeignKey
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..diabetes.services.db import Base, SessionLocal, run_db
from ..diabetes.services.repository import commit
from ..types import SessionProtocol

logger = logging.getLogger(__name__)


class AssistantMemory(Base):
    __tablename__ = "assistant_memory"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


async def save_summary(user_id: int, summary_text: str) -> None:
    """Persist ``summary_text`` for ``user_id``."""

    def _save(session: SessionProtocol) -> None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        now = datetime.now(timezone.utc)
        if record is None:
            record = AssistantMemory(
                user_id=user_id, summary_text=summary_text, updated_at=now
            )
            cast(Session, session).add(record)
        else:
            record.summary_text = summary_text
            record.updated_at = now
        commit(cast(Session, session))

    await run_db(_save, sessionmaker=SessionLocal)


async def get_summary(user_id: int) -> str | None:
    """Return stored summary for ``user_id`` or ``None``."""

    def _get(session: SessionProtocol) -> str | None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        return record.summary_text if record else None

    return await run_db(_get, sessionmaker=SessionLocal)


async def delete_summary(user_id: int) -> None:
    """Remove stored summary for ``user_id`` if present."""

    def _del(session: SessionProtocol) -> None:
        record = cast(AssistantMemory | None, session.get(AssistantMemory, user_id))
        if record is None:
            return
        session.delete(record)
        commit(cast(Session, session))

    await run_db(_del, sessionmaker=SessionLocal)


__all__ = ["AssistantMemory", "save_summary", "get_summary", "delete_summary"]
