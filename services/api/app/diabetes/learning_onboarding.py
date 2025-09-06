from __future__ import annotations

from typing import MutableMapping, cast

from telegram import Update
from telegram.ext import ContextTypes


async def learn_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset learning onboarding progress stored in ``user_data``."""

    message = update.effective_message
    if message is None:
        return
    user_data = cast(MutableMapping[str, object], context.user_data)
    user_data.pop("learn_profile_overrides", None)
    user_data.pop("learn_onboarding_stage", None)
    await message.reply_text("Учебный онбординг сброшен.")


__all__ = ["learn_reset"]
