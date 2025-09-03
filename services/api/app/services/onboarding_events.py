from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from ..diabetes.services.db import SessionLocal, run_db
from ..diabetes.services.repository import commit
from ..models.onboarding_metrics import OnboardingEvent
from ..types import SessionProtocol


async def log_event(step: str, variant: str | None) -> None:
    """Persist onboarding event for metrics."""
    if variant is None:
        variant = "unknown"

    def _save(session: SessionProtocol) -> None:
        event = OnboardingEvent(variant=variant, step=step)
        cast(Session, session).add(event)
        commit(cast(Session, session))

    await run_db(_save, sessionmaker=SessionLocal)


__all__ = ["log_event"]
