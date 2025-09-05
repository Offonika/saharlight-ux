from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..schemas.user import UserContext
from ..telegram_auth import require_tg_user
from ..services.onboarding_events import OnboardingEvent, log_onboarding_event
from ..services import onboarding_state
from ..diabetes.services.db import SessionLocal, run_db

logger = logging.getLogger(__name__)

PROFILE, TIMEZONE, REMINDERS = range(3)

router = APIRouter(prefix="/api/onboarding")


class EventPayload(BaseModel):
    event: str
    step: int | None = None
    meta: dict[str, Any] | None = None


@router.post("/events")
async def post_event(
    payload: EventPayload, user: UserContext = Depends(require_tg_user)
) -> dict[str, bool]:
    variant = None
    if payload.meta and isinstance(payload.meta.get("variant"), str):
        variant = payload.meta["variant"]
    step = payload.step or 0

    def _log(session: Session) -> None:
        log_onboarding_event(session, user["id"], payload.event, step, variant)

    await run_db(_log, sessionmaker=SessionLocal)
    return {"ok": True}


class StatusResponse(BaseModel):
    completed: bool
    step: str | None
    missing: list[str]


@router.get("/status", response_model=StatusResponse)
async def get_status(user: UserContext = Depends(require_tg_user)) -> StatusResponse:
    user_id = user["id"]
    state = await onboarding_state.load_state(user_id)

    def _has_finished(session: Session) -> bool:
        return (
            session.query(OnboardingEvent)
            .filter(
                OnboardingEvent.user_id == user_id,
                OnboardingEvent.event_name == "onboarding_finished",
            )
            .first()
            is not None
        )

    finished = await run_db(_has_finished, sessionmaker=SessionLocal)

    if (state and state.completed_at) or finished:
        return StatusResponse(completed=True, step=None, missing=[])

    if state and state.step == REMINDERS:
        return StatusResponse(
            completed=False, step="reminders", missing=["reminders"]
        )

    return StatusResponse(
        completed=False, step="profile", missing=["profile", "reminders"]
    )
