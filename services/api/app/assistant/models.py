from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.diabetes.services.db import Base


class AssistantMemory(Base):
    """Minimal assistant context stored per user."""

    __tablename__ = "assistant_memory"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    profile_url: Mapped[str | None] = mapped_column(String, nullable=True)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_turn_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


__all__ = ["AssistantMemory"]
