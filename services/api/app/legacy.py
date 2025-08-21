import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from .services.audit import log_patient_access
from .schemas.profile import ProfileSchema
from .schemas.reminders import ReminderSchema
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
async def profiles_get(telegram_id: int) -> ProfileSchema:
    profile = await get_profile(telegram_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    icr: float | None = profile.icr
    cf: float | None = profile.cf
    target_bg: float | None = profile.target_bg
    low_threshold: float | None = profile.low_threshold
    high_threshold: float | None = profile.high_threshold

    return ProfileSchema(
        telegram_id=profile.telegram_id,
        icr=float(icr) if icr is not None else 0.0,
        cf=float(cf) if cf is not None else 0.0,
        target=float(target_bg) if target_bg is not None else 0.0,
        low=float(low_threshold) if low_threshold is not None else 0.0,
        high=float(high_threshold) if high_threshold is not None else 0.0,
        org_id=profile.org_id,
    )


@router.get("/api/reminders", dependencies=[Depends(require_tg_user)])
async def api_reminders(
    telegram_id: int,
    request: Request,
    id: int | None = None,
) -> list[dict[str, object]] | dict[str, object]:
    log_patient_access(getattr(request.state, "user_id", None), telegram_id)
    rems = await list_reminders(telegram_id)
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


@router.post("/api/reminders", dependencies=[Depends(require_tg_user)])
async def api_reminders_post(data: ReminderSchema) -> dict[str, object]:
    rid = await save_reminder(data)
    return {"status": "ok", "id": rid}
