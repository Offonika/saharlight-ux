from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import BigInteger, ForeignKey, Integer, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.diabetes.services.db import Base, User


class LearningProgress(Base):
    """Track user's progress through a learning plan."""

    __tablename__ = "learning_progress"
    __table_args__ = (
        sa.Index("learning_progress_user_plan_idx", "user_id", "plan_id"),
        sa.Index("learning_progress_updated_at_idx", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    user: Mapped[User] = relationship(
        "User", back_populates="learning_progresses"
    )


__all__ = ["LearningProgress"]
