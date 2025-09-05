from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..diabetes.services.repository import commit
from ..models.onboarding_event import OnboardingEvent

logger = logging.getLogger(__name__)

__all__ = ["log_onboarding_event"]


def log_onboarding_event(
    session: Session,
    user_id: int,
    event: str,
    step: str | None = None,
    meta: dict[str, object] | None = None,
    variant: str | None = None,
) -> None:
    """Persist an onboarding analytics event."""

    event_row = OnboardingEvent(
        user_id=user_id,
        event=event,
        step=step,
        meta_json=dict(meta) if meta is not None else None,
        variant=variant,
    )
    session.add(event_row)
    commit(session)
