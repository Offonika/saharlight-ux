from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..diabetes.services.db import SessionLocal, run_db
from ..diabetes.services.repository import commit
from ..models.onboarding_event import OnboardingEvent
from . import onboarding_state

logger = logging.getLogger(__name__)

__all__ = ["log_onboarding_event", "onboarding_status"]


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


async def onboarding_status(user_id: int) -> tuple[bool, str | None, list[str]]:
    """Return onboarding status for ``user_id``.

    Completion is detected if there is a recent ``onboarding_completed`` event
    or the :class:`~services.api.app.services.onboarding_state.OnboardingState`
    has ``completed_at`` set.  A recent event is one newer than 14 days.
    If the most recent event is ``onboarding_canceled`` the onboarding is
    considered incomplete regardless of state.
    """

    REMINDERS_STEP = 2

    state = await onboarding_state.load_state(user_id)

    def _last_event(session: Session) -> str | None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        row = (
            session.execute(
                sa.select(OnboardingEvent.event)
                .where(
                    OnboardingEvent.user_id == user_id,
                    OnboardingEvent.event.in_(["onboarding_completed", "onboarding_canceled"]),
                    OnboardingEvent.ts >= cutoff,
                )
                .order_by(OnboardingEvent.ts.desc())
            )
            .scalars()
            .first()
        )
        return row

    last_event = await run_db(_last_event, sessionmaker=SessionLocal)

    if last_event == "onboarding_canceled":
        state = None
        completed = False
    elif last_event == "onboarding_completed":
        completed = True
    else:
        completed = state is not None and state.completed_at is not None

    if completed:
        return True, None, []

    if state and state.step == REMINDERS_STEP:
        return False, "reminders", ["reminders"]

    return False, "profile", ["profile", "reminders"]
