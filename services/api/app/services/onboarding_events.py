from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, ForeignKey, Integer, String, TIMESTAMP, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..diabetes.services.db import Base, SessionLocal, run_db
from ..diabetes.services.repository import commit
from . import onboarding_state

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


PROFILE, TIMEZONE, REMINDERS = range(3)

VARIANT_ORDER: dict[str | None, list[int]] = {
    "A": [PROFILE, TIMEZONE, REMINDERS],
    "B": [TIMEZONE, PROFILE, REMINDERS],
    None: [PROFILE, TIMEZONE, REMINDERS],
}

STALE_PERIOD = timedelta(days=14)

__all__ = [
    "OnboardingEvent",
    "log_onboarding_event",
    "get_onboarding_status",
    "PROFILE",
    "TIMEZONE",
    "REMINDERS",
]


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


async def get_onboarding_status(user_id: int) -> tuple[int | None, list[int]]:
    """Return next onboarding step and list of missing steps."""

    state = await onboarding_state.load_state(user_id)
    now = datetime.now(timezone.utc)

    if state is not None and state.completed_at is not None:
        return None, []

    def _latest_event(session: Session) -> OnboardingEvent | None:
        stmt = (
            select(OnboardingEvent)
            .where(OnboardingEvent.user_id == user_id)
            .order_by(OnboardingEvent.created_at.desc())
            .limit(1)
        )
        return session.scalars(stmt).first()

    last = await run_db(_latest_event, sessionmaker=SessionLocal)

    if last is not None and last.event_name == "onboarding_completed":
        created = last.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if now - created < STALE_PERIOD:
            return None, []

    variant = state.variant if state is not None else (last.variant if last else None)
    order = VARIANT_ORDER.get(variant, VARIANT_ORDER[None])
    step = state.step if state is not None else order[0]
    idx = order.index(step)
    missing = order[idx:]
    return step, missing
