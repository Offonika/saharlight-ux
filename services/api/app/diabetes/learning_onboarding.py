"""Learning mode onboarding utilities."""

from __future__ import annotations

import logging
from typing import Mapping, cast

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# Questions asked during the onboarding flow.
AGE_PROMPT = "Укажите вашу возрастную группу."
DIABETES_TYPE_PROMPT = "Укажите тип диабета."
LEARNING_LEVEL_PROMPT = "Укажите ваш уровень знаний."

_PROMPTS: Mapping[str, str] = {
    "age_group": AGE_PROMPT,
    "diabetes_type": DIABETES_TYPE_PROMPT,
    "learning_level": LEARNING_LEVEL_PROMPT,
}

_KEYBOARDS: Mapping[str, ReplyKeyboardMarkup] = {
    "age_group": ReplyKeyboardMarkup(
        [["teen", "adult"], ["60+"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    ),
    "diabetes_type": ReplyKeyboardMarkup(
        [["T1", "T2"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    ),
    "learning_level": ReplyKeyboardMarkup(
        [["novice", "intermediate", "expert"]],
        resize_keyboard=True,
        one_time_keyboard=True,
    ),
}

_ORDER = ["age_group", "diabetes_type", "learning_level"]


def _norm_age_group(raw: str) -> str | None:
    """Normalize age group value from *raw* input."""

    text = raw.strip().lower()
    if not text:
        return None
    if text.isdigit():
        age = int(text)
        if age >= 60:
            return "60+"
        if age >= 18:
            return "adult"
        if age >= 13:
            return "teen"
        return "child"
    mapping = {
        "teen": "teen",
        "подросток": "teen",
        "adult": "adult",
        "взрослый": "adult",
        "60+": "60+",
        "senior": "60+",
        "elder": "60+",
    }
    return mapping.get(text)


def _norm_diabetes_type(raw: str) -> str | None:
    """Normalize diabetes type from *raw* input."""

    text = raw.strip().lower().replace(" ", "")
    mapping = {
        "1": "T1",
        "t1": "T1",
        "type1": "T1",
        "тип1": "T1",
        "2": "T2",
        "t2": "T2",
        "type2": "T2",
        "тип2": "T2",
    }
    return mapping.get(text)


def _norm_level(raw: str) -> str | None:
    """Normalize learning level from *raw* input."""

    text = raw.strip().lower()
    mapping = {
        "0": "novice",
        "1": "intermediate",
        "2": "expert",
        "novice": "novice",
        "beginner": "novice",
        "intermediate": "intermediate",
        "advanced": "expert",
        "expert": "expert",
        "pro": "expert",
    }
    return mapping.get(text)


async def ensure_overrides(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure learning mode prerequisites are satisfied.

    Sequentially ask the user for ``age_group``, ``diabetes_type`` and
    ``learning_level``. Answers are stored in
    ``ctx.user_data['learn_profile_overrides']`` in normalized form. While
    onboarding is in progress the function returns ``False`` so that callers can
    stop further processing. ``True`` is returned once all fields are collected.
    """

    user_data = cast(dict[str, object], context.user_data)
    overrides = cast(
        dict[str, str], user_data.setdefault("learn_profile_overrides", {})
    )
    message = update.message
    stage = cast(str | None, user_data.get("learn_onboarding_stage"))
    raw_text = getattr(message, "text", None)
    text = raw_text.strip() if raw_text else None

    if stage and text:
        norm: str | None
        if stage == "age_group":
            norm = _norm_age_group(text)
        elif stage == "diabetes_type":
            norm = _norm_diabetes_type(text)
        else:
            norm = _norm_level(text)
        if norm is None:
            if message is not None:
                await message.reply_text(
                    _PROMPTS[stage], reply_markup=_KEYBOARDS.get(stage)
                )
            return False
        overrides[stage] = norm
        user_data.pop("learn_onboarding_stage", None)
        stage = None

    for key in _ORDER:
        if not overrides.get(key):
            user_data["learn_onboarding_stage"] = key
            if message is not None:
                await message.reply_text(
                    _PROMPTS[key], reply_markup=_KEYBOARDS.get(key)
                )
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

