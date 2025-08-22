import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .services.audit import log_patient_access
from .schemas.profile import ProfileSchema
from .schemas.reminders import ReminderSchema
from .schemas.user import UserContext
from .services.profile import get_profile, save_profile
from .services.reminders import list_reminders, save_reminder
from .telegram_auth import require_tg_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/profiles")
async def profiles_post(data: ProfileSchema) -> dict[str, str]:
    await save_profile(data)
    return {"status": "ok"}


@router.get("/profiles")
async def profiles_get(
    telegramId: int | None = Query(None),
    telegram_id: int | None = Query(None, alias="telegram_id"),
) -> ProfileSchema:
    tid = telegramId or telegram_id
    if tid is None:
        raise HTTPException(status_code=422, detail="telegramId is required")
    profile = await get_profile(tid)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    icr: float | None = profile.icr
    cf: float | None = profile.cf
    target_bg: float | None = profile.target_bg
    low_threshold: float | None = profile.low_threshold
    high_threshold: float | None = profile.high_threshold

    return ProfileSchema(
        telegramId=profile.telegram_id,
        icr=float(icr) if icr is not None else 0.0,
        cf=float(cf) if cf is not None else 0.0,
        target=float(target_bg) if target_bg is not None else 0.0,
        low=float(low_threshold) if low_threshold is not None else 0.0,
        high=float(high_threshold) if high_threshold is not None else 0.0,
        orgId=profile.org_id,
    )


@router.get("/reminders")
async def api_reminders(
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
        request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Request-Id")
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
    return {}


@router.post("/reminders", dependencies=[Depends(require_tg_user)])
async def api_reminders_post(data: ReminderSchema) -> dict[str, object]:
    rid = await save_reminder(data)
    return {"status": "ok", "id": rid}
