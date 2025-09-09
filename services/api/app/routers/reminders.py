import logging
from datetime import datetime
from typing import Literal, Optional, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import config, reminder_events
from ..schemas.reminders import ReminderSchema
from ..schemas.user import UserContext
from ..services.reminders import (
    delete_reminder as remove_reminder,
    list_reminders,
    save_reminder,
)
from ..services.audit import log_patient_access
from ..telegram_auth import check_token


class ReminderError(Exception):
    """Reminder notification failure."""


logger = logging.getLogger(__name__)

router = APIRouter()


async def _post_job_queue_event(action: Literal["saved", "deleted"], rid: int) -> None:
    if reminder_events.job_queue is not None:
        try:
            if action == "saved":
                await reminder_events.notify_reminder_saved(rid)
            else:
                reminder_events.notify_reminder_deleted(rid)
        except (ReminderError, RuntimeError, httpx.HTTPError):
            logger.exception(
                "failed to notify job queue: action=%s reminder_id=%s",
                action,
                rid,
            )
        return
    base = config.get_settings().api_url
    if not base:
        raise RuntimeError("API_URL not configured")
    url = f"{base.rstrip('/')}/internal/reminders/{action}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json={"id": rid})
        except httpx.HTTPError:  # pragma: no cover - network errors
            logger.exception(
                "failed to notify job queue: action=%s reminder_id=%s",
                action,
                rid,
            )
            return
        if not 200 <= resp.status_code < 300:
            logger.error(
                "failed to notify job queue: action=%s reminder_id=%s status=%s body=%s",
                action,
                rid,
                resp.status_code,
                resp.text,
            )


@router.get("/reminders")
async def get_reminders(
    request: Request,
    telegramId: int | None = Query(None),
    telegram_id: int | None = Query(None, alias="telegram_id"),
    user: UserContext = Depends(check_token),
) -> list[dict[str, object]]:
    tid = telegramId or telegram_id
    if tid is None:
        raise HTTPException(status_code=422, detail="telegramId is required")
    if tid != user["id"]:
        request_id = request.headers.get("X-Request-ID") or request.headers.get(
            "X-Request-Id"
        )
        logger.warning(
            "request_id=%s telegramId=%s does not match user_id=%s",
            request_id,
            tid,
            user["id"],
        )
        raise HTTPException(status_code=404, detail="reminder not found")
    log_patient_access(getattr(request.state, "user_id", None), tid)

    rems = await list_reminders(tid)
    result: list[dict[str, object]] = []
    for r in rems:
        last = cast(Optional[datetime], getattr(r, "last_fired_at", None))
        next_ = cast(Optional[datetime], getattr(r, "next_at", None))
        result.append(
            {
                "telegramId": r.telegram_id,
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "kind": r.kind,
                "time": r.time.strftime("%H:%M") if r.time else None,
                "intervalHours": r.interval_hours,
                "intervalMinutes": r.interval_minutes,
                "minutesAfter": r.minutes_after,
                "daysOfWeek": r.daysOfWeek,
                "isEnabled": r.is_enabled,
                "orgId": r.org_id,
                "nextAt": next_.isoformat() if next_ else None,
                "lastFiredAt": last.isoformat() if last else None,
                "fires7d": cast(int, getattr(r, "fires7d", 0)),
            }
        )
    return result


@router.get("/reminders/{id}")
async def get_reminder(
    request: Request,
    id: int,
    telegramId: int | None = Query(None),
    telegram_id: int | None = Query(None, alias="telegram_id"),
    user: UserContext = Depends(check_token),
) -> dict[str, object]:
    tid = telegramId or telegram_id
    if tid is None:
        raise HTTPException(status_code=422, detail="telegramId is required")
    if tid != user["id"]:
        request_id = request.headers.get("X-Request-ID") or request.headers.get(
            "X-Request-Id"
        )
        logger.warning(
            "request_id=%s telegramId=%s does not match user_id=%s",
            request_id,
            tid,
            user["id"],
        )
        raise HTTPException(status_code=404, detail="reminder not found")
    log_patient_access(getattr(request.state, "user_id", None), tid)

    rems = await list_reminders(tid)
    for r in rems:
        if r.id == id:
            last = cast(Optional[datetime], getattr(r, "last_fired_at", None))
            next_ = cast(Optional[datetime], getattr(r, "next_at", None))
            return {
                "telegramId": r.telegram_id,
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "kind": r.kind,
                "time": r.time.strftime("%H:%M") if r.time else None,
                "intervalHours": r.interval_hours,
                "intervalMinutes": r.interval_minutes,
                "minutesAfter": r.minutes_after,
                "daysOfWeek": r.daysOfWeek,
                "isEnabled": r.is_enabled,
                "orgId": r.org_id,
                "nextAt": next_.isoformat() if next_ else None,
                "lastFiredAt": last.isoformat() if last else None,
                "fires7d": cast(int, getattr(r, "fires7d", 0)),
            }
    raise HTTPException(status_code=404, detail="reminder not found")


@router.post("/reminders")
async def post_reminder(
    data: ReminderSchema,
    user: UserContext = Depends(check_token),
) -> dict[str, object]:
    if data.telegramId != user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")
    rid = await save_reminder(data)
    await _post_job_queue_event("saved", rid)
    return {"status": "ok", "id": rid}


@router.patch("/reminders")
async def patch_reminder(
    data: ReminderSchema,
    user: UserContext = Depends(check_token),
) -> dict[str, object]:
    if data.id is None:
        raise HTTPException(status_code=422, detail="id is required")
    if data.telegramId != user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")
    rid = await save_reminder(data)
    await _post_job_queue_event("saved", rid)
    return {"status": "ok", "id": rid}


@router.delete("/reminders")
async def delete_reminder(
    request: Request,
    telegramId: int | None = Query(None),
    telegram_id: int | None = Query(None, alias="telegram_id"),
    id: int | None = None,
    user: UserContext = Depends(check_token),
) -> dict[str, str]:
    tid = telegramId or telegram_id
    if tid is None or id is None:
        raise HTTPException(status_code=422, detail="telegramId and id are required")
    if tid != user["id"]:
        request_id = request.headers.get("X-Request-ID") or request.headers.get(
            "X-Request-Id"
        )
        logger.warning(
            "request_id=%s telegramId=%s does not match user_id=%s",
            request_id,
            tid,
            user["id"],
        )
        raise HTTPException(status_code=404, detail="reminder not found")
    log_patient_access(getattr(request.state, "user_id", None), tid)
    await remove_reminder(tid, id)
    await _post_job_queue_event("deleted", id)
    return {"status": "ok"}
