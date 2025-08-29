import logging
from datetime import time

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from .routers.reminders import router as reminders_router
from .schemas.profile import ProfileSchema
from .services.profile import get_profile, save_profile
from .diabetes.services.db import User as UserDB, run_db
from .diabetes.services.repository import CommitError, commit

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(reminders_router)


@router.post("/profiles", operation_id="profilesPost", tags=["profiles"])
async def profiles_post(data: ProfileSchema) -> ProfileSchema:
    try:
        await save_profile(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    def _save_user(session: Session) -> None:
        user = session.get(UserDB, data.telegramId)
        if user is None:
            user = UserDB(telegram_id=data.telegramId, thread_id="api")
            session.add(user)
        user.timezone = data.timezone
        user.timezone_auto = data.timezoneAuto
        try:
            commit(session)
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save_user)
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

    def _get_user(session: Session) -> UserDB | None:
        return session.get(UserDB, tid)

    user = await run_db(_get_user)
    tz = user.timezone if user else "UTC"
    tz_auto = user.timezone_auto if user else True

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
        quietStart=profile.quiet_start or time(23, 0),
        quietEnd=profile.quiet_end or time(7, 0),
        orgId=profile.org_id,
        sosContact=profile.sos_contact or "",
        sosAlertsEnabled=(
            profile.sos_alerts_enabled
            if profile.sos_alerts_enabled is not None
            else True
        ),
        timezone=tz,
        timezoneAuto=tz_auto,
    )
