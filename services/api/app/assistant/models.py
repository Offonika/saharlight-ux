from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.diabetes.services.db import Base, User


class LessonLog(Base):
    """Conversation log entry for a lesson."""

    __tablename__ = "lesson_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), index=True, nullable=False
    )
    plan_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    module_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    step_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User")


__all__ = ["LessonLog"]
