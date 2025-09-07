"""Learning mode onboarding utilities."""

from __future__ import annotations

import logging
from typing import Callable, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from services.api.app.assistant.repositories import plans

logger = logging.getLogger(__name__)


def _norm_age_group(text: str) -> str | None:
    """Normalize *text* to a known age group."""

    t = text.strip().lower()
    if t.isdigit():
        age = int(t)
        if age < 18:
            return "teen"
        if age >= 60:
            return "60+"
        return "adult"
    mapping = {
        "teen": "teen",
        "adult": "adult",
        "60+": "60+",
    }
    return mapping.get(t)


def _norm_diabetes_type(text: str) -> str | None:
    """Normalize *text* to a diabetes type code."""

    t = text.strip().lower().replace(" ", "")
    if t in {"1", "t1", "type1", "i"}:
        return "T1"
    if t in {"2", "t2", "type2", "ii"}:
        return "T2"
    return None


def _norm_level(text: str) -> str | None:
    """Normalize *text* to a learning level."""

    t = text.strip().lower()
    if t.isdigit():
        num_map: dict[int, str] = {0: "novice", 1: "intermediate", 2: "expert"}
        return num_map.get(int(t))
    str_map: dict[str, str] = {
        "novice": "novice",
        "beginner": "novice",
        "новичок": "novice",
        "intermediate": "intermediate",
        "средний": "intermediate",
        "продвинутый": "intermediate",
        "advanced": "expert",
        "expert": "expert",
        "эксперт": "expert",
    }
    return str_map.get(t)


# Questions asked during the onboarding flow.
AGE_PROMPT = "Укажите вашу возрастную группу."
DIABETES_TYPE_PROMPT = "Укажите тип диабета."
LEARNING_LEVEL_PROMPT = "Укажите ваш уровень знаний."


CB_PREFIX = "learn_onb:"

_ORDER: list[
    tuple[
        str,
        str,
        Callable[[str], str | None],
        InlineKeyboardMarkup,
    ]
] = [
    (
        "age_group",
        AGE_PROMPT,
        _norm_age_group,
        InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("teen", callback_data=f"{CB_PREFIX}teen"),
                    InlineKeyboardButton("adult", callback_data=f"{CB_PREFIX}adult"),
                    InlineKeyboardButton("60+", callback_data=f"{CB_PREFIX}60+"),
                ]
            ]
        ),
    ),
    (
        "diabetes_type",
        DIABETES_TYPE_PROMPT,
        _norm_diabetes_type,
        InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("T1", callback_data=f"{CB_PREFIX}T1"),
                    InlineKeyboardButton("T2", callback_data=f"{CB_PREFIX}T2"),
                ]
            ]
        ),
    ),
    (
        "learning_level",
        LEARNING_LEVEL_PROMPT,
        _norm_level,
        InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Новичок", callback_data=f"{CB_PREFIX}novice"),
                    InlineKeyboardButton(
                        "Средний", callback_data=f"{CB_PREFIX}intermediate"
                    ),
                    InlineKeyboardButton("Эксперт", callback_data=f"{CB_PREFIX}expert"),
                ]
            ]
        ),
    ),
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
    message: Message | None = update.message
    if message is None and update.callback_query is not None:
        message = cast("Message | None", update.callback_query.message)
    for key, prompt, norm, keyboard in _ORDER:
        raw = overrides.get(key)
        if raw is not None:
            normalized = norm(raw)
            if normalized is not None:
                overrides[key] = normalized
                continue
            overrides.pop(key, None)
        if message is not None:
            await message.reply_text(prompt, reply_markup=keyboard)
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
    user = update.effective_user
    if user is not None:
        active_plan = await plans.get_active_plan(user.id)
        if active_plan is not None and active_plan.id is not None:
            await plans.deactivate_plan(user.id, active_plan.id)
    message = update.message
    if message is not None:
        await message.reply_text("Learning onboarding reset. Отправьте /learn.")
