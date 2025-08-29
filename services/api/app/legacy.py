import logging
from datetime import time

from fastapi import APIRouter, HTTPException, Query

from .routers.reminders import router as reminders_router
from .schemas.profile import ProfileSchema
from .services.profile import get_profile, save_profile

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(reminders_router)


@router.post("/profiles", operation_id="profilesPost", tags=["profiles"])
async def profiles_post(data: ProfileSchema) -> ProfileSchema:
    try:
        await save_profile(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return data


@router.get("/profiles", operation_id="profilesGet", tags=["profiles"])
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
    cf_val: float | None = profile.cf
    target_bg: float | None = profile.target_bg
    low_threshold: float | None = profile.low_threshold
    high_threshold: float | None = profile.high_threshold

    return ProfileSchema(
        telegramId=profile.telegram_id,
        icr=float(icr) if icr is not None else 0.0,
        cf=float(cf_val) if cf_val is not None else 0.0,
        target=float(target_bg) if target_bg is not None else 0.0,
        low=float(low_threshold) if low_threshold is not None else 0.0,
        high=float(high_threshold) if high_threshold is not None else 0.0,
        quietStart=profile.quiet_start or time(23, 0),
        quietEnd=profile.quiet_end or time(7, 0),
        orgId=profile.org_id,
        sosContact=profile.sos_contact or "",
        sosAlertsEnabled=(
            profile.sos_alerts_enabled
            if profile.sos_alerts_enabled is not None
            else True
        ),
    )
