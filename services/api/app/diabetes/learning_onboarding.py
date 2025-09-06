"""Learning mode onboarding utilities."""

from __future__ import annotations

from typing import cast

from telegram import Update
from telegram.ext import ContextTypes


ONBOARDING_PROMPT = "Перед началом ответьте 'да' чтобы продолжить обучение."


async def ensure_overrides(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Ensure learning mode prerequisites are satisfied.

    If the user has not yet answered the onboarding question, send it and
    return ``False`` so that the calling handler can stop further processing.
    ``True`` is returned once the onboarding question has been answered.
    """

    user_data = cast(dict[str, object] | None, getattr(context, "user_data", None))
    if user_data is None:
        user_data = {}
        setattr(context, "user_data", user_data)
    if user_data.get("learning_onboarded"):
        return True
    message = update.message
    if message is not None:
        await message.reply_text(ONBOARDING_PROMPT)
    user_data["learning_waiting"] = True
    return False

