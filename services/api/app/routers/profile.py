"""Profile related endpoints."""

from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..diabetes.schemas.profile import ProfileSettingsIn
from ..diabetes.services import db as db_module
from ..diabetes.services.db import User
from ..schemas.profile import ProfileSchema
from ..schemas.user import UserContext
from ..services.profile import (
    get_profile_settings,
    patch_user_settings,
    save_profile,
)
from ..telegram_auth import check_token


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/profile/self")
async def profile_self(user: UserContext = Depends(check_token)) -> UserContext:
    """Return current user context."""

    return user


@router.get("/profile", response_model=ProfileSchema)
async def profile(user: UserContext = Depends(check_token)) -> ProfileSchema:
    """Return current profile settings."""

    def _get(session: Session) -> User | None:
        return cast(User | None, session.get(User, user["id"]))

    db_user = await db_module.run_db(_get, sessionmaker=db_module.SessionLocal)
    if db_user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if not db_user.onboarding_complete:
        raise HTTPException(status_code=422, detail="onboarding incomplete")

    return await get_profile_settings(user["id"])


@router.patch("/profile", response_model=ProfileSchema)
async def profile_patch(
    data: ProfileSettingsIn,
    device_tz: str | None = Query(None, alias="deviceTz"),
    user: UserContext = Depends(check_token),
) -> ProfileSchema:
    """Update profile settings."""

    return await patch_user_settings(user["id"], data, device_tz)


@router.post("/profile")
async def profile_post(
    data: ProfileSchema,
    user: UserContext = Depends(check_token),
) -> dict[str, str]:
    """Create or overwrite full profile settings."""

    if data.telegramId != user["id"]:
        raise HTTPException(status_code=403, detail="telegramId mismatch")
    try:
        await save_profile(data)
    except ValueError as exc:  # pragma: no cover - conversion to HTTP 422
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok"}
