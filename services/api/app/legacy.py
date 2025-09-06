import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import exc as sqlalchemy_exc

from .routers.reminders import router as reminders_router
from .schemas.profile import ProfilePatchSchema
from .services.profile import get_profile, save_profile, patch_user_settings
from .diabetes.schemas.profile import (
    CarbUnits,
    GlucoseUnits,
    ProfileSettingsIn,
    ProfileSettingsOut,
    RapidInsulinType,
    TherapyType,
)

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(reminders_router)


@router.post("/profiles", operation_id="profilesPost", tags=["profiles"])
async def profiles_post(data: ProfilePatchSchema) -> ProfilePatchSchema:
    try:
        await save_profile(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    settings = ProfileSettingsIn.model_validate(data.model_dump(exclude_unset=True))
    if settings.model_fields_set:
        await patch_user_settings(data.telegramId, settings)
    return data


@router.patch("/profiles", operation_id="profilesPatch", tags=["profiles"])
async def profiles_patch(data: ProfilePatchSchema) -> ProfilePatchSchema:
    return await profiles_post(data)


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
