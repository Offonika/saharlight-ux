import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..schemas.reminders import ReminderSchema
from ..schemas.user import UserContext
from ..services.reminders import list_reminders, save_reminder
from ..services.audit import log_patient_access
from ..telegram_auth import require_tg_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/reminders")
async def get_reminders(
    request: Request,
    telegramId: int | None = Query(None),
    telegram_id: int | None = Query(None, alias="telegram_id"),
    id: int | None = None,
    user: UserContext = Depends(require_tg_user),
) -> list[dict[str, object]] | dict[str, object]:
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
        raise HTTPException(status_code=403)
    log_patient_access(getattr(request.state, "user_id", None), tid)

    rems = await list_reminders(tid)
    if id is None:
        return [
            {
                "id": r.id,
                "type": r.type,
                "title": r.type,
                "time": r.time,
                "active": r.is_enabled,
                "interval": r.interval_hours,
            }
            for r in rems
        ]
    for r in rems:
        if r.id == id:
            return {
                "id": r.id,
                "type": r.type,
                "title": r.type,
                "time": r.time,
                "active": r.is_enabled,
                "interval": r.interval_hours,
            }
    raise HTTPException(status_code=404, detail="reminder not found")


@router.post("/reminders", dependencies=[Depends(require_tg_user)])
async def post_reminder(data: ReminderSchema) -> dict[str, object]:
    rid = await save_reminder(data)
    return {"status": "ok", "id": rid}
