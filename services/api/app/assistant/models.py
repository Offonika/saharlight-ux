from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.diabetes.services.db import Base


class AssistantMemory(Base):
    """Conversation memory summary for a user."""

    __tablename__ = "assistant_memory"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_turn_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


__all__ = ["AssistantMemory"]
