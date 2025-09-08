from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .. import reminder_events
from ..config import settings


def _require_internal_token(
    token: str | None = Header(None, alias="X-Internal-API-Key"),
) -> None:
    if not token or token != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="invalid token")


class ReminderId(BaseModel):
    id: int


router = APIRouter(prefix="/internal/reminders")


@router.post("/saved")
async def reminder_saved(
    data: ReminderId, _: None = Depends(_require_internal_token)
) -> dict[str, str]:
    await reminder_events.notify_reminder_saved(data.id)
    return {"status": "ok"}


@router.post("/deleted")
async def reminder_deleted(
    data: ReminderId, _: None = Depends(_require_internal_token)
) -> dict[str, str]:
    reminder_events.notify_reminder_deleted(data.id)
    return {"status": "ok"}
