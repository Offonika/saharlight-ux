"""Learning mode onboarding utilities."""

from __future__ import annotations

from typing import cast

from telegram import Update
from telegram.ext import ContextTypes


async def ensure_overrides(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure learning mode is allowed for the user.

    This is a stub implementation that always allows learning mode.
    """

    return True


async def learn_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear learning onboarding data from the user context."""

    message = update.effective_message
    if message is None:
        return
    user_data = cast(dict[str, object], ctx.user_data)
    user_data.pop("learn_profile_overrides", None)
    user_data.pop("learn_onboarding_stage", None)
    await message.reply_text("Учебный онбординг сброшен.")


__all__ = ["ensure_overrides", "learn_reset"]
