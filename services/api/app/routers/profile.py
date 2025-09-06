"""Profile related endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from ..diabetes.schemas.profile import ProfileSettingsIn, ProfileSettingsOut
from ..schemas.user import UserContext
from ..services.profile import get_profile_settings, patch_user_settings
from ..telegram_auth import require_tg_user


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/profile/self")
async def profile_self(user: UserContext = Depends(require_tg_user)) -> UserContext:
    """Return current user context."""

    return user


@router.get("/profile", response_model=ProfileSettingsOut)
async def profile(user: UserContext = Depends(require_tg_user)) -> ProfileSettingsOut:
    """Return current profile settings."""

    return await get_profile_settings(user["id"])


@router.patch("/profile", response_model=ProfileSettingsOut)
async def profile_patch(
    data: ProfileSettingsIn,
    device_tz: str | None = Query(None, alias="deviceTz"),
    user: UserContext = Depends(require_tg_user),
) -> ProfileSettingsOut:
    """Update profile settings."""

    return await patch_user_settings(user["id"], data, device_tz)

