from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, TIMESTAMP, JSON, func
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.diabetes.services.db import Base


class OnboardingEvent(Base):
    """DB model for recorded onboarding events."""

    __tablename__ = "onboarding_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    event: Mapped[str] = mapped_column(String, nullable=False)
    step: Mapped[str | None] = mapped_column(String)
    ts: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    meta_json: Mapped[dict[str, object] | None] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )
    variant: Mapped[str | None] = mapped_column(String)


__all__ = ["OnboardingEvent"]
