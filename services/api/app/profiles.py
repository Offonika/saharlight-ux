from __future__ import annotations

from typing import cast

from telegram.ext import ContextTypes

from ..rest_client import _auth_headers, get_json


async def get_profile_for_user(
    _: int, ctx: ContextTypes.DEFAULT_TYPE
) -> dict[str, object]:
    if await _auth_headers(ctx):
        db_profile = await get_json("/profile/self", ctx)
    else:
        db_profile = {}

    user_data = ctx.user_data or {}
    overrides = cast(dict[str, object], user_data.get("learn_profile_overrides", {}))
    profile = {**db_profile, **overrides}
    profile.setdefault("age_group", "adult")
    profile.setdefault("diabetes_type", "unknown")
    profile.setdefault("learning_level", "novice")
    return profile
