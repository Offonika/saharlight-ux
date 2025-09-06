
from __future__ import annotations

import logging
import time
from typing import Any, Mapping, MutableMapping, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from services.api.app.config import TOPICS_RU, settings
from services.api.app.ui.keyboard import build_main_keyboard
from . import curriculum_engine
from .handlers import learning_handlers as legacy_handlers
from .learning_onboarding import ensure_overrides
from .learning_state import LearnState, clear_state, get_state, set_state
from .services.gpt_client import format_reply
from .services.lesson_log import add_lesson_log

logger = logging.getLogger(__name__)

RATE_LIMIT_SECONDS = 3.0
RATE_LIMIT_MESSAGE = "⏳ Подождите немного перед следующим запросом."


def choose_initial_topic(profile: Mapping[str, str | None]) -> str:
    """Pick an initial topic slug based on ``profile``.

    Currently this is a simple heuristic that returns the first available
    topic.  More sophisticated logic can be implemented later.
    """

    return next(iter(TOPICS_RU))


def _rate_limited(user_data: MutableMapping[str, Any], key: str) -> bool:
    """Return ``True`` if action identified by ``key`` is too frequent."""

    now = time.monotonic()
    last = cast(float | None, user_data.get(key))
    if last is not None and now - last < RATE_LIMIT_SECONDS:
        return True
    user_data[key] = now
    return False


def _get_profile(user_data: MutableMapping[str, Any]) -> Mapping[str, str | None]:
    raw = user_data.get("learn_profile_overrides")
    if isinstance(raw, Mapping):
        return raw
    return {}


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show an inline keyboard with available learning topics."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    if settings.learning_content_mode == "static":
        await legacy_handlers.learn_command(update, context)
        return
    if not await ensure_overrides(update, context):
        return
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(title, callback_data=f"lesson:{slug}")]
            for slug, title in TOPICS_RU.items()
        ]
    )
    await message.reply_text("Выберите тему:", reply_markup=build_main_keyboard())
    await message.reply_text("Доступные темы:", reply_markup=keyboard)


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start learning or display topics depending on configuration."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    if settings.learning_content_mode == "static":
        await legacy_handlers.learn_command(update, context)
        return
    if settings.learning_ui_show_topics:
        await topics_command(update, context)
        return
    if not await ensure_overrides(update, context):
        return
    user = update.effective_user
    if user is None:
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    profile = _get_profile(user_data)
    slug = choose_initial_topic(profile)
    progress = await curriculum_engine.start_lesson(user.id, slug)
    user_data["lesson_id"] = progress.lesson_id
    text, _ = await curriculum_engine.next_step(user.id, progress.lesson_id)
    if text is None:
        return
    text = format_reply(text)
    await message.reply_text(text, reply_markup=build_main_keyboard())
    await add_lesson_log(user.id, slug, "assistant", 1, text)
    state = LearnState(
        topic=slug,
        step=1,
        awaiting_answer=True,
        last_step_text=text,
    )
    set_state(user_data, state)


async def _start_lesson(
    message: Message,
    user_data: MutableMapping[str, Any],
    topic_slug: str,
) -> None:
    """Start a lesson and send the first step."""

    from_user = getattr(message, "from_user", None)
    user_id = from_user.id if from_user else None
    if user_id is None:
        return
    progress = await curriculum_engine.start_lesson(user_id, topic_slug)
    user_data["lesson_id"] = progress.lesson_id
    text, _ = await curriculum_engine.next_step(user_id, progress.lesson_id)
    if text is None:
        return
    text = format_reply(text)
    await message.reply_text(text, reply_markup=build_main_keyboard())
    await add_lesson_log(user_id, topic_slug, "assistant", 1, text)
    state = LearnState(
        topic=topic_slug,
        step=1,
        awaiting_answer=True,
        last_step_text=text,
    )
    set_state(user_data, state)


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a lesson by topic slug passed as an argument."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    if settings.learning_content_mode == "static":
        await legacy_handlers.lesson_command(update, context)
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    if _rate_limited(user_data, "_lesson_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    topic_slug = context.args[0] if context.args else None
    if topic_slug is None:
        await message.reply_text(
            "Сначала выберите тему командой /learn"
        )
        return
    await _start_lesson(message, user_data, topic_slug)


async def lesson_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle topic selection from inline keyboard."""

    query = update.callback_query
    if query is None:
        return
    raw_message = query.message
    if not settings.learning_mode_enabled:
        await query.answer()
        if raw_message is not None and hasattr(raw_message, "reply_text"):
            await cast(Message, raw_message).reply_text(
                "режим обучения отключён"
            )
        return
    if settings.learning_content_mode == "static":
        await legacy_handlers.lesson_command(update, context)
        return
    await query.answer()
    if raw_message is None or not hasattr(raw_message, "reply_text"):
        return
    message = cast(Message, raw_message)
    user_data = cast(MutableMapping[str, Any], context.user_data)
    if _rate_limited(user_data, "_lesson_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    data = query.data or ""
    slug = data.split(":", 1)[1] if ":" in data else ""
    await _start_lesson(message, user_data, slug)


async def lesson_answer_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Process user's answer and move to the next step."""

    message = update.message
    if message is None or not message.text:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    from_user = getattr(message, "from_user", None)
    if settings.learning_content_mode == "static":
        await legacy_handlers.quiz_answer_handler(update, context)
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    state = get_state(user_data)
    if state is None or not state.awaiting_answer:
        return
    if _rate_limited(user_data, "_answer_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    lesson_id = cast(int | None, user_data.get("lesson_id"))
    if lesson_id is None:
        return
    user_id = from_user.id if from_user else None
    if user_id is None:
        return
    user_text = message.text.strip()
    await add_lesson_log(user_id, state.topic, "user", state.step, user_text)
    _correct, feedback = await curriculum_engine.check_answer(
        user_id, lesson_id, user_text, state.last_step_text or ""
    )
    feedback = format_reply(feedback)
    await message.reply_text(feedback, reply_markup=build_main_keyboard())
    await add_lesson_log(user_id, state.topic, "assistant", state.step, feedback)
    next_text, _completed = await curriculum_engine.next_step(
        user_id, lesson_id, feedback
    )
    if next_text is None:
        return
    next_text = format_reply(next_text)
    await message.reply_text(next_text, reply_markup=build_main_keyboard())
    await add_lesson_log(
        user_id, state.topic, "assistant", state.step + 1, next_text
    )
    state.step += 1
    state.last_step_text = next_text
    state.prev_summary = feedback
    state.awaiting_answer = True
    set_state(user_data, state)


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit the current lesson and clear stored state."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    if settings.learning_content_mode == "static":
        await legacy_handlers.exit_command(update, context)
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    clear_state(user_data)
    user_data.pop("lesson_id", None)
    await message.reply_text(
        "Учебная сессия завершена.", reply_markup=build_main_keyboard()
    )


__all__ = [
    "topics_command",
    "learn_command",
    "lesson_command",
    "lesson_callback",
    "lesson_answer_handler",
    "exit_command",
]
