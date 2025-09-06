import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import exc as sqlalchemy_exc
from sqlalchemy.orm import Session

from .routers.reminders import router as reminders_router
from .schemas.profile import ProfileSchema
from .services.profile import get_profile, save_profile
from .diabetes.schemas.profile import (
    CarbUnits,
    GlucoseUnits,
    ProfileSettingsOut,
    RapidInsulinType,
    TherapyType,
)
from .diabetes.services.db import Profile, run_db
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

    def _save_profile_settings(session: Session) -> None:
        profile = session.get(Profile, data.telegramId)
        if profile is None:
            profile = Profile(telegram_id=data.telegramId)
            session.add(profile)
        profile.timezone = data.timezone
        profile.timezone_auto = data.timezoneAuto
        if data.therapyType is not None:
            profile.therapy_type = data.therapyType
        try:
            commit(session)
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save_profile_settings)
    return data


@router.get("/profiles", operation_id="profilesGet", tags=["profiles"])
async def profiles_get(
    telegramId: int | None = Query(None),
    telegram_id: int | None = Query(None, alias="telegram_id"),
) -> ProfileSettingsOut:
    tid = telegramId or telegram_id
    if tid is None:
        raise HTTPException(status_code=422, detail="telegramId is required")
    if tid <= 0:
        raise HTTPException(status_code=422, detail="telegramId must be positive")
    try:
        profile = await get_profile(tid)
    except HTTPException:
        logger.warning("failed to fetch profile %s", tid)
        raise
    except (ConnectionError, sqlalchemy_exc.OperationalError) as exc:
        logger.exception("failed to fetch profile %s", tid)
        raise HTTPException(status_code=503, detail="database temporarily unavailable") from exc
    except Exception as exc:
        logger.exception("failed to fetch profile %s", tid)
        raise HTTPException(status_code=500, detail="database connection failed") from exc

    tz = profile.timezone if profile.timezone else "UTC"
    tz_auto = profile.timezone_auto if profile.timezone_auto is not None else True

    return ProfileSettingsOut(
        timezone=tz,
        timezoneAuto=tz_auto,
        dia=profile.dia,
        roundStep=profile.round_step,
        carbUnits=CarbUnits(profile.carb_units),
        gramsPerXe=profile.grams_per_xe,
        glucoseUnits=GlucoseUnits(profile.glucose_units),
        sosContact=profile.sos_contact,
        sosAlertsEnabled=(
            profile.sos_alerts_enabled
            if profile.sos_alerts_enabled is not None
            else True
        ),
        therapyType=TherapyType(profile.therapy_type),
        rapidInsulinType=(
            RapidInsulinType(profile.insulin_type)
            if profile.insulin_type
            else None
        ),
        maxBolus=profile.max_bolus,
        preBolus=profile.prebolus_min,
        afterMealMinutes=profile.postmeal_check_min,
    )
