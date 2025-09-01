from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .. import reminder_events


class ReminderId(BaseModel):
    id: int


router = APIRouter(prefix="/internal/reminders")


@router.post("/saved")
async def reminder_saved(data: ReminderId) -> dict[str, str]:
    await reminder_events.notify_reminder_saved(data.id)
    return {"status": "ok"}


@router.post("/deleted")
async def reminder_deleted(data: ReminderId) -> dict[str, str]:
    reminder_events.notify_reminder_deleted(data.id)
    return {"status": "ok"}
