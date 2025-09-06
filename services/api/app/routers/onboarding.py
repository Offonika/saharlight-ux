from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..schemas.user import UserContext
from ..telegram_auth import require_tg_user
from ..services.onboarding_events import log_onboarding_event
from ..diabetes.services.db import (
    Profile,
    Reminder,
    SessionLocal,
    run_db,
)
from ..models.onboarding_event import OnboardingEvent

logger = logging.getLogger(__name__)

PROFILE, TIMEZONE, REMINDERS = range(3)

router = APIRouter(prefix="/api/onboarding")


class EventPayload(BaseModel):
    event: str
    step: int | None = None
    meta: dict[str, Any] | None = None


@router.post("/events")
async def post_event(payload: EventPayload, user: UserContext = Depends(require_tg_user)) -> dict[str, bool]:
    variant = None
    if payload.meta and isinstance(payload.meta.get("variant"), str):
        variant = payload.meta["variant"]
    step = str(payload.step or 0)

    def _log(session: Session) -> None:
        log_onboarding_event(session, user["id"], payload.event, step, variant=variant)

    await run_db(_log, sessionmaker=SessionLocal)
    return {"ok": True}


class StatusResponse(BaseModel):
    completed: bool
    step: str | None
    missing: list[str]


@router.get("/status", response_model=StatusResponse)
async def get_status(user: UserContext = Depends(require_tg_user)) -> StatusResponse:
    user_id = user["id"]

    def _load(session: Session) -> tuple[Profile | None, int, OnboardingEvent | None]:
        profile = session.get(Profile, user_id)
        reminders = session.execute(
            sa.select(sa.func.count()).select_from(Reminder).where(Reminder.telegram_id == user_id, Reminder.is_enabled)
        ).scalar_one()
        last_event = session.scalars(
            sa.select(OnboardingEvent).where(OnboardingEvent.user_id == user_id).order_by(OnboardingEvent.ts.desc())
        ).first()
        return profile, reminders, last_event

    profile, reminders, last_event = await run_db(_load, sessionmaker=SessionLocal)

    profile_valid = (
        profile is not None
        and profile.timezone is not None
        and profile.icr is not None
        and profile.cf is not None
        and profile.target_bg is not None
        and profile.low_threshold is not None
        and profile.high_threshold is not None
    )

    skipped = bool(
        last_event
        and last_event.event == "onboarding_completed"
        and isinstance(last_event.meta_json, dict)
        and last_event.meta_json.get("skippedReminders")
    )

    completed = profile_valid and (reminders > 0 or skipped)

    if completed and (not last_event or last_event.event != "onboarding_completed"):

        def _log(session: Session) -> None:
            log_onboarding_event(session, user_id, "onboarding_completed", str(REMINDERS))

        await run_db(_log, sessionmaker=SessionLocal)

    if completed:
        return StatusResponse(completed=True, step=None, missing=[])

    if not profile_valid:
        return StatusResponse(completed=False, step="profile", missing=["profile", "reminders"])

    return StatusResponse(completed=False, step="reminders", missing=["reminders"])
