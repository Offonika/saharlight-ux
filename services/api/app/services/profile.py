from __future__ import annotations

import logging
from fastapi import HTTPException
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..diabetes.services.db import Profile, User
from ..diabetes.services import db
from ..diabetes.services.repository import CommitError, commit
from ..schemas.profile import ProfileSchema
from ..diabetes.schemas.profile import (
    CarbUnits,
    ProfileSettingsIn,
    ProfileSettingsOut,
    TherapyType,
    RapidInsulinType,
)
from ..types import SessionProtocol

logger = logging.getLogger(__name__)


__all__ = [
    "set_timezone",
    "save_timezone",
    "patch_user_settings",
    "save_profile",
    "get_profile",
]


async def set_timezone(telegram_id: int, tz: str) -> None:  # pragma: no cover
    """Backward-compatible helper to update only timezone."""

    await patch_user_settings(
        telegram_id,
        ProfileSettingsIn(timezone=tz),
    )


async def save_timezone(telegram_id: int, tz: str, *, auto: bool) -> None:
    """Save timezone and ``timezoneAuto`` flag for a user."""

    await patch_user_settings(
        telegram_id,
        ProfileSettingsIn(timezone=tz, timezoneAuto=auto),
    )


async def patch_user_settings(
    telegram_id: int,
    data: ProfileSettingsIn,
    device_tz: str | None = None,
) -> ProfileSettingsOut:
    """Persist user settings, updating only provided fields."""

    if data.timezone is not None:
        try:
            ZoneInfo(data.timezone)
        except ZoneInfoNotFoundError as exc:  # pragma: no cover - validation
            raise HTTPException(status_code=400, detail="invalid timezone") from exc
    if device_tz is not None:
        try:
            ZoneInfo(device_tz)
        except ZoneInfoNotFoundError as exc:  # pragma: no cover - validation
            raise HTTPException(
                status_code=400, detail="invalid device timezone"
            ) from exc

    def _patch(session: SessionProtocol) -> ProfileSettingsOut:
        user = cast(User | None, session.get(User, telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, thread_id="api")
            cast(Session, session).add(user)

        profile = cast(Profile | None, session.get(Profile, telegram_id))
        if profile is None:
            profile = Profile(telegram_id=telegram_id)
            cast(Session, session).add(profile)

        if data.timezone is not None:
            profile.timezone = data.timezone
        if data.timezoneAuto is not None:
            profile.timezone_auto = data.timezoneAuto
        if data.dia is not None:
            profile.dia = data.dia
        if data.roundStep is not None:
            profile.round_step = data.roundStep
        if data.carbUnits is not None:
            profile.carb_units = data.carbUnits.value
        if data.gramsPerXe is not None:
            profile.grams_per_xe = data.gramsPerXe
        if data.sosContact is not None:
            profile.sos_contact = data.sosContact
        if data.sosAlertsEnabled is not None:
            profile.sos_alerts_enabled = data.sosAlertsEnabled
        if data.therapyType is not None:
            profile.therapy_type = data.therapyType.value
        if data.rapidInsulinType is not None:
            profile.insulin_type = data.rapidInsulinType.value
        if data.maxBolus is not None:
            profile.max_bolus = data.maxBolus
        if data.preBolus is not None:
            profile.prebolus_min = data.preBolus
        if data.afterMealMinutes is not None:
            profile.postmeal_check_min = data.afterMealMinutes

        if profile.timezone_auto and device_tz and profile.timezone != device_tz:
            profile.timezone = device_tz

        try:
            commit(cast(Session, session))
        except CommitError:  # pragma: no cover
            raise HTTPException(status_code=500, detail="db commit failed")

        return ProfileSettingsOut(
            timezone=profile.timezone,
            timezoneAuto=profile.timezone_auto,
            dia=profile.dia,
            roundStep=profile.round_step,
            carbUnits=CarbUnits(profile.carb_units),
            gramsPerXe=profile.grams_per_xe,
            sosContact=profile.sos_contact,
            sosAlertsEnabled=profile.sos_alerts_enabled,
            therapyType=TherapyType(profile.therapy_type),
            rapidInsulinType=(
                RapidInsulinType(profile.insulin_type) if profile.insulin_type else None
            ),
            maxBolus=profile.max_bolus,
            preBolus=profile.prebolus_min,
            afterMealMinutes=profile.postmeal_check_min,
        )

    return await db.run_db(_patch, sessionmaker=db.SessionLocal)


def _validate_profile(data: ProfileSchema) -> None:
    """Validate business rules for a patient profile."""
    required = {
        "target": data.target,
        "low": data.low,
        "high": data.high,
    }
    if data.therapyType in {"insulin", "mixed"}:
        required["icr"] = data.icr
        required["cf"] = data.cf
    for name, value in required.items():
        if value is None:
            raise ValueError(f"{name} is required")  # pragma: no cover
        if value <= 0:
            raise ValueError(f"{name} must be greater than 0")  # pragma: no cover

    low = cast(float, data.low)
    high = cast(float, data.high)
    target = cast(float, data.target)

    if low >= high:
        raise ValueError("low must be less than high")  # pragma: no cover

    if not (low < target < high):
        raise ValueError("target must be between low and high")  # pragma: no cover

    # quiet times are validated by Pydantic; no additional checks required


async def save_profile(data: ProfileSchema) -> None:
    _validate_profile(data)

    def _save(session: SessionProtocol) -> None:
        user = cast(User | None, session.get(User, data.telegramId))
        if user is None:
            user = User(telegram_id=data.telegramId, thread_id="api")
            cast(Session, session).add(user)

        profile_data = {
            "telegram_id": data.telegramId,
            "org_id": data.orgId,
            "icr": data.icr,
            "cf": data.cf,
            "target_bg": data.target,
            "low_threshold": data.low,
            "high_threshold": data.high,
            "quiet_start": data.quietStart,
            "quiet_end": data.quietEnd,
            "sos_contact": data.sosContact,
            "sos_alerts_enabled": (
                data.sosAlertsEnabled if data.sosAlertsEnabled is not None else True
            ),
            "timezone": data.timezone,
            "timezone_auto": data.timezoneAuto,
        }

        stmt = insert(Profile).values(**profile_data)
        update_values = {
            key: getattr(stmt.excluded, key)
            for key in profile_data.keys()
            if key != "telegram_id"
        }
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Profile.telegram_id],
                set_=update_values,
            )
        )

        try:
            commit(cast(Session, session))
        except CommitError:  # pragma: no cover
            raise HTTPException(status_code=500, detail="db commit failed")

    await db.run_db(_save, sessionmaker=db.SessionLocal)


async def get_profile(telegram_id: int) -> Profile:
    if telegram_id <= 0:
        raise HTTPException(status_code=422, detail="telegramId must be positive")

    def _get(session: SessionProtocol) -> Profile | None:
        return cast(Profile | None, session.get(Profile, telegram_id))

    try:
        profile = await db.run_db(_get, sessionmaker=db.SessionLocal)
    except Exception as exc:  # pragma: no cover - unexpected DB error
        logger.exception("failed to fetch profile %s", telegram_id)
        raise HTTPException(status_code=500, detail="db error") from exc

    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    return profile
