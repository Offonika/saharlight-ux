"""Learning mode onboarding utilities."""

from __future__ import annotations

import logging
from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# Questions asked during the onboarding flow.
AGE_PROMPT = "Укажите вашу возрастную группу."
DIABETES_TYPE_PROMPT = "Укажите тип диабета."
LEARNING_LEVEL_PROMPT = "Укажите ваш уровень знаний."

_ORDER = [
    ("age_group", AGE_PROMPT),
    ("diabetes_type", DIABETES_TYPE_PROMPT),
    ("learning_level", LEARNING_LEVEL_PROMPT),
]


async def ensure_overrides(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure learning mode prerequisites are satisfied.

    Sequentially ask the user for ``age_group``, ``diabetes_type`` and
    ``learning_level``. Answers are stored in
    ``ctx.user_data['learn_profile_overrides']``. While onboarding is in
    progress the function returns ``False`` so that callers can stop further
    processing. ``True`` is returned once all fields are collected.
    """

    user_data = cast(dict[str, object], context.user_data)
    overrides = cast(
        dict[str, str], user_data.setdefault("learn_profile_overrides", {})
    )
    for key, prompt in _ORDER:
        if not overrides.get(key):
            message = update.message
            if message is not None:
                await message.reply_text(prompt)
            user_data["learn_onboarding_stage"] = key
            return False
    user_data.pop("learn_onboarding_stage", None)
    user_data["learning_onboarded"] = True
    return True


async def learn_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset learning-related state for the user."""

    logger.debug("learn_reset", extra={"user": update.effective_user})
    user_data = cast(dict[str, object], context.user_data)
    for key in [
        "learning_onboarded",
        "learn_profile_overrides",
        "learn_onboarding_stage",
    ]:
        user_data.pop(key, None)
    message = update.message
    if message is not None:
        await message.reply_text("Learning onboarding reset. Отправьте /learn.")
