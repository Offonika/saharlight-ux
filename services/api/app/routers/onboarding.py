from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..schemas.user import UserContext
from ..telegram_auth import require_tg_user
from ..services.onboarding_events import log_onboarding_event, onboarding_status
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
    step = str(payload.step or 0)

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
    completed, step, missing = await onboarding_status(user["id"])
    return StatusResponse(completed=completed, step=step, missing=missing)
