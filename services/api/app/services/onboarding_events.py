from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..diabetes.services.db import Base
from ..diabetes.services.repository import commit

logger = logging.getLogger(__name__)


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
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    variant: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["OnboardingEvent", "log_onboarding_event"]


def log_onboarding_event(
    session: Session,
    user_id: int,
    event_name: str,
    step: int,
    variant: str | None,
) -> None:
    """Persist an onboarding analytics event."""

    event = OnboardingEvent(
        user_id=user_id, event_name=event_name, step=step, variant=variant
    )
    session.add(event)
    commit(session)
