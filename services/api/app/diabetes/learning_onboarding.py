"""Learning mode onboarding utilities."""

from __future__ import annotations

import logging
from typing import Callable, Mapping, cast

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from services.api.app import profiles
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
        "подросток": "teen",
        "adult": "adult",
        "взрослый": "adult",
        "60+": "60+",
    }
    return mapping.get(t)


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
        "продвинутый": "expert",
        "advanced": "expert",
        "expert": "expert",
        "эксперт": "expert",
    }
    return str_map.get(t)


def needs_age(profile_db: Mapping[str, object]) -> bool:
    """Return ``True`` if user's age group is missing."""

    value = profile_db.get("age_group")
    return not isinstance(value, str) or value == ""


def needs_level(profile_db: Mapping[str, object]) -> bool:
    """Return ``True`` if learning level is missing."""

    value = profile_db.get("learning_level")
    return not isinstance(value, str) or value == ""


# Questions asked during the onboarding flow.
AGE_PROMPT = "Укажите вашу возрастную группу."
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
                    InlineKeyboardButton("Подросток", callback_data=f"{CB_PREFIX}teen"),
                    InlineKeyboardButton("Взрослый", callback_data=f"{CB_PREFIX}adult"),
                    InlineKeyboardButton("60+", callback_data=f"{CB_PREFIX}60+"),
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
                    InlineKeyboardButton(
                        "Продвинутый", callback_data=f"{CB_PREFIX}expert"
                    ),
                ]
            ]
        ),
    ),
]


async def ensure_overrides(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure learning mode prerequisites are satisfied.

    Sequentially ask the user for ``age_group`` and ``learning_level``. Answers are stored in
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

    profile: Mapping[str, object] = {}
    user = update.effective_user
    if user is not None:
        try:
            profile = await profiles.get_profile_for_user(user.id, context)
        except (httpx.HTTPError, RuntimeError):
            logger.exception("Failed to get profile for user %s", user.id)
            profile = {}
    has_age = "age_group" in overrides or not needs_age(profile)
    has_level = "learning_level" in overrides or not needs_level(profile)
    asked = "age" if not has_age else "level" if has_age and not has_level else "none"
    logger.info(
        "ensure_overrides",
        extra={
            "user_id": getattr(user, "id", None),
            "has_age": has_age,
            "has_level": has_level,
            "asked": asked,
        },
    )
    for key, prompt, norm, keyboard in _ORDER:
        if key == "age_group" and not needs_age(profile):
            val = profile.get("age_group")
            if isinstance(val, str):
                normalized = norm(val)
                if normalized is not None:
                    overrides[key] = normalized
                    continue
        if key == "learning_level" and not needs_level(profile):
            val = profile.get("learning_level")
            if isinstance(val, str):
                normalized = norm(val)
                if normalized is not None:
                    overrides[key] = normalized
                    continue
        raw = overrides.get(key)
        if raw is not None:
            normalized = norm(raw)
            if normalized is not None:
                overrides[key] = normalized
                continue
            overrides.pop(key, None)
        if message is not None:
            if key == "age_group":
                logger.info("onboarding_question", extra={"reason": "needs_age"})
            elif key == "learning_level":
                logger.info("onboarding_question", extra={"reason": "needs_level"})
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
