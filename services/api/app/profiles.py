from __future__ import annotations

from typing import cast

import httpx
from telegram.ext import ContextTypes

from ..rest_client import get_json


async def get_profile_for_user(
    _: int, ctx: ContextTypes.DEFAULT_TYPE
) -> dict[str, object]:
    try:
        base = await get_json("/profile/self", ctx)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            base = {}
        else:  # pragma: no cover - re-raise unexpected errors
            raise

    try:
        db_profile = await get_json("/learning-profile", ctx)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            db_profile = {}
        else:  # pragma: no cover - re-raise unexpected errors
            raise

    user_data = ctx.user_data or {}
    overrides = cast(
        dict[str, object], user_data.get("learn_profile_overrides", {})
    )
    profile = {**base, **db_profile, **overrides}
    profile.setdefault("age_group", "adult")
    profile.setdefault("diabetes_type", "unknown")
    profile.setdefault("learning_level", "novice")
    return profile
