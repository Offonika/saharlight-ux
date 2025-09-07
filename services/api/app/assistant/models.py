from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, TIMESTAMP
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
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_turn_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(
        String(1024), nullable=False, default=""
    )


class LessonLog(Base):
    """Stores conversation steps within a learning plan."""

    __tablename__ = "lesson_logs"
    __table_args__ = (sa.Index("ix_lesson_logs_user_plan", "user_id", "plan_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False
    )
    module_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    step_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
    )


__all__ = ["AssistantMemory", "LessonLog"]
