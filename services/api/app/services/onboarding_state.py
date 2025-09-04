from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import cast

from sqlalchemy import BigInteger, Integer, String, JSON, TIMESTAMP, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..diabetes.services.db import Base, SessionLocal, run_db
from ..diabetes.services.repository import commit
from ..types import SessionProtocol

logger = logging.getLogger(__name__)


class OnboardingState(Base):
    __tablename__ = "onboarding_states"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    variant: Mapped[str | None] = mapped_column(String)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


async def save_state(user_id: int, step: int, data: dict[str, object], variant: str | None = None) -> None:
    """Persist onboarding state for a user."""

    def _save(session: SessionProtocol) -> None:
        state = cast(OnboardingState | None, session.get(OnboardingState, user_id))
        if state is None:
            state = OnboardingState(user_id=user_id)
            cast(Session, session).add(state)
        state.step = step
        state.data = dict(data)
        if variant is not None:
            state.variant = variant
        state.updated_at = datetime.now(timezone.utc)
        commit(cast(Session, session))

    await run_db(_save, sessionmaker=SessionLocal)


async def load_state(user_id: int) -> OnboardingState | None:
    """Load onboarding state for a user.

    Records older than 14 days are removed and ``None`` is returned.
    """

    def _load(session: SessionProtocol) -> OnboardingState | None:
        state = cast(OnboardingState | None, session.get(OnboardingState, user_id))
        if state is None:
            return None
        updated = (
            state.updated_at if state.updated_at.tzinfo is not None else state.updated_at.replace(tzinfo=timezone.utc)
        )
        if datetime.now(timezone.utc) - updated >= timedelta(days=14):
            session.delete(state)
            commit(cast(Session, session))
            return None
        return state

    return await run_db(_load, sessionmaker=SessionLocal)


async def complete_state(user_id: int) -> None:
    """Mark onboarding as completed for ``user_id``."""

    def _complete(session: SessionProtocol) -> None:
        state = cast(OnboardingState | None, session.get(OnboardingState, user_id))
        if state is None:
            return
        now = datetime.now(timezone.utc)
        state.completed_at = now
        state.updated_at = now
        commit(cast(Session, session))

    await run_db(_complete, sessionmaker=SessionLocal)
