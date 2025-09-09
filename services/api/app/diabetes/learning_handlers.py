from __future__ import annotations

import logging
import time
from typing import Any, Mapping, MutableMapping, cast

import httpx
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from services.api.app.config import TOPICS_RU, settings
from services.api.app.ui.keyboard import build_main_keyboard
from .dynamic_tutor import BUSY_MESSAGE, check_user_answer, generate_step_text
from .handlers import learning_handlers as legacy_handlers
from ..ui.keyboard import LEARN_BUTTON_TEXT
from .learning_onboarding import ensure_overrides
from .learning_state import LearnState, clear_state, get_state, set_state
from .learning_utils import choose_initial_topic
# Re-export the curriculum engine so tests and callers can patch it easily.
# Including it in ``__all__`` below marks the import as used for the linter.
from . import curriculum_engine as curriculum_engine
from .curriculum_engine import LessonNotFoundError
from .learning_prompts import build_system_prompt, disclaimer
from .llm_router import LLMTask
from .services.gpt_client import (
    create_learning_chat_completion,
    format_reply,
)
from services.api.app.assistant.repositories.logs import add_lesson_log
from services.api.app.assistant.repositories import plans as plans_repo
from services.api.app.assistant.repositories import (
    learning_profile as learning_profile_repo,
)
from services.api.app.assistant.services import progress_service
from .planner import generate_learning_plan, pretty_plan

logger = logging.getLogger(__name__)

PLANS_KEY = "learning_plans"
PROGRESS_KEY = "learning_progress"
BUSY_KEY = "learn_busy"

RATE_LIMIT_SECONDS = 3.0
RATE_LIMIT_MESSAGE = "⏳ Подождите немного перед следующим запросом."


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


async def _persist(
    user_id: int,
    user_data: MutableMapping[str, Any],
    bot_data: MutableMapping[str, object],
) -> None:
    plans = cast(dict[int, Any], bot_data.setdefault(PLANS_KEY, {}))
    progress = cast(dict[int, Any], bot_data.setdefault(PROGRESS_KEY, {}))
    raw_plan = user_data.get("learning_plan")
    plan: list[str] | None = raw_plan if isinstance(raw_plan, list) else None
    raw_plan_id = user_data.get("learning_plan_id")
    plan_id: int | None = raw_plan_id if isinstance(raw_plan_id, int) else None
    if plan is not None:
        plans[user_id] = plan
        try:
            if plan_id is None:
                active = await plans_repo.get_active_plan(user_id)
                if active is None:
                    plan_id = await plans_repo.create_plan(user_id, 1, plan)
                else:
                    plan_id = active.id
                user_data["learning_plan_id"] = plan_id
            else:
                await plans_repo.update_plan(plan_id, plan_json=plan)
        except (
            SQLAlchemyError,
            RuntimeError,
        ) as exc:  # pragma: no cover - logging only
            logger.exception("persist plan failed: %s", exc)
            plan_id = None
    state = get_state(user_data)
    if state is not None and plan_id is not None:
        data = {
            "topic": state.topic,
            "module_idx": cast(int, user_data.get("learning_module_idx", 0)),
            "step_idx": state.step,
            "snapshot": state.last_step_text,
            "prev_summary": state.prev_summary,
        }
        progress[user_id] = data
        try:
            await progress_service.upsert_progress(user_id, plan_id, data)
        except (
            SQLAlchemyError,
            RuntimeError,
        ) as exc:  # pragma: no cover - logging only
            logger.exception("persist progress failed: %s", exc)


async def _hydrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user is None:
        return True
    user_data = cast(MutableMapping[str, Any], context.user_data)
    try:
        stored_profile = await learning_profile_repo.get_learning_profile(user.id)
    except (SQLAlchemyError, RuntimeError) as exc:  # pragma: no cover - logging only
        logger.exception("profile hydrate failed: %s", exc)
    else:
        if isinstance(stored_profile, Mapping):
            user_data["learn_profile_overrides"] = dict(stored_profile)
            age_group = stored_profile.get("age_group")
            level = stored_profile.get("learning_level")
            if isinstance(age_group, str) and isinstance(level, str):
                user_data["learning_onboarded"] = True
    if get_state(user_data) is not None:
        return True
    if "learning_plan" in user_data and "learning_plan_index" in user_data:
        return True
    bot_data = cast(MutableMapping[str, Any], context.bot_data)
    plans_map = cast(dict[int, Any], bot_data.setdefault(PLANS_KEY, {}))
    progress_map = cast(
        dict[int, dict[str, Any]], bot_data.setdefault(PROGRESS_KEY, {})
    )
    data = progress_map.get(user.id)
    raw_plan = plans_map.get(user.id)
    plan: list[str] | None = raw_plan if isinstance(raw_plan, list) else None
    raw_plan_id = user_data.get("learning_plan_id")
    plan_id: int | None = raw_plan_id if isinstance(raw_plan_id, int) else None
    if data is None or plan is None or plan_id is None:
        try:
            db_plan = await plans_repo.get_active_plan(user.id)
            if db_plan is None:
                return True
            plan = db_plan.plan_json
            plan_id = db_plan.id
            db_progress = await progress_service.get_progress(user.id, plan_id)
            if db_progress is None:
                return True
            data = db_progress.progress_json
            plans_map[user.id] = plan
            progress_map[user.id] = data
            user_data["learning_plan_id"] = plan_id
        except (
            SQLAlchemyError,
            RuntimeError,
        ) as exc:  # pragma: no cover - logging only
            logger.exception("hydrate failed: %s", exc)
            return True
    topic = cast(str, data.get("topic", ""))
    module_idx = cast(int, data.get("module_idx", 0))
    step_idx = cast(int, data.get("step_idx", 0))
    snapshot = cast(str | None, data.get("snapshot"))
    prev_summary = cast(str | None, data.get("prev_summary"))
    user_data["learning_module_idx"] = module_idx
    user_data["learning_plan"] = plan
    if plan is None or not 0 <= step_idx < len(plan):
        step_idx = 0
        user_data["learning_plan_index"] = 0
    else:
        user_data["learning_plan_index"] = step_idx - 1 if step_idx > 0 else 0
    if snapshot is None:
        profile = _get_profile(user_data)
        snapshot = await generate_step_text(profile, topic, step_idx, prev_summary)
        if snapshot == BUSY_MESSAGE:
            message = update.effective_message
            if message is not None:
                await message.reply_text(
                    BUSY_MESSAGE, reply_markup=build_main_keyboard()
                )
            return False
        data["snapshot"] = snapshot
        progress_map[user.id] = data
        try:
            await progress_service.upsert_progress(user.id, plan_id, data)
        except (
            SQLAlchemyError,
            RuntimeError,
        ) as exc:  # pragma: no cover - logging only
            logger.exception("snapshot persist failed: %s", exc)
    state = LearnState(
        topic=topic,
        step=step_idx,
        last_step_text=snapshot,
        prev_summary=prev_summary,
        awaiting=True,
    )
    set_state(user_data, state)
    return True


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
    if not await _hydrate(update, context):
        return
    user = update.effective_user
    if user is None:
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    state = get_state(user_data)
    if state is not None and state.last_step_text:
        await message.reply_text(
            state.last_step_text, reply_markup=build_main_keyboard()
        )
        return
    if not await ensure_overrides(update, context):
        return
    profile = _get_profile(user_data)
    slug, _ = choose_initial_topic(profile)
    logger.info(
        "learn_start", extra={"content_mode": "dynamic", "branch": "dynamic"}
    )
    try:
        await curriculum_engine.start_lesson(user.id, slug)
    except LessonNotFoundError:
        logger.warning(
            "no_static_lessons; run dynamic",
            extra={"hint": "make load-lessons"},
        )
        await message.reply_text(
            "Не нашёл учебные записи, пробую динамический режим…",
            reply_markup=build_main_keyboard(),
        )
    text = await generate_step_text(profile, slug, 1, None)
    if text == BUSY_MESSAGE:
        await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
        return
    plan = generate_learning_plan(text)
    user_data["learning_plan"] = plan
    user_data["learning_plan_index"] = 0
    text = format_reply(plan[0])
    await message.reply_text(text, reply_markup=build_main_keyboard())
    await add_lesson_log(
        user.id,
        0,
        cast(int, user_data.get("learning_module_idx", 0)),
        1,
        "assistant",
        "",
    )
    state = LearnState(
        topic=slug,
        step=1,
        last_step_text=text,
        awaiting=True,
    )
    set_state(user_data, state)
    await _persist(user.id, user_data, context.bot_data)


async def _start_lesson(
    message: Message,
    user_data: MutableMapping[str, Any],
    bot_data: MutableMapping[str, object],
    profile: Mapping[str, str | None],
    topic_slug: str,
) -> None:
    """Start lesson, send first step and store progress."""

    from_user = getattr(message, "from_user", None)
    if from_user is None:
        return
    logger.info(
        "learn_start", extra={"content_mode": "dynamic", "branch": "dynamic"}
    )
    try:
        await curriculum_engine.start_lesson(from_user.id, topic_slug)
    except LessonNotFoundError:
        logger.warning(
            "no_static_lessons; run dynamic",
            extra={"hint": "make load-lessons"},
        )
        await message.reply_text(
            "Не нашёл учебные записи, пробую динамический режим…",
            reply_markup=build_main_keyboard(),
        )
    text = await generate_step_text(profile, topic_slug, 1, None)
    if text == BUSY_MESSAGE:
        await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
        return
    if not text.startswith(disclaimer()):
        text = f"{disclaimer()}\n\n{text}"
    plan = generate_learning_plan(text)
    user_data["learning_plan"] = plan
    user_data["learning_plan_index"] = 0
    text = format_reply(plan[0])
    await message.reply_text(text, reply_markup=build_main_keyboard())
    await add_lesson_log(
        from_user.id,
        0,
        cast(int, user_data.get("learning_module_idx", 0)),
        1,
        "assistant",
        "",
    )
    state = LearnState(
        topic=topic_slug,
        step=1,
        last_step_text=text,
        awaiting=True,
    )
    set_state(user_data, state)
    await _persist(from_user.id, user_data, bot_data)


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
    if not await ensure_overrides(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    if _rate_limited(user_data, "_lesson_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    topic_slug = context.args[0] if context.args else None
    if topic_slug is None:
        await message.reply_text(
            f"Сначала выберите тему — нажмите кнопку {LEARN_BUTTON_TEXT} или команду /learn"
        )
        return
    if topic_slug not in TOPICS_RU:
        await message.reply_text("Неизвестная тема")
        return
    profile = _get_profile(user_data)
    if not await _hydrate(update, context):
        return
    await _start_lesson(message, user_data, context.bot_data, profile, topic_slug)


async def lesson_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle topic selection from inline keyboard."""

    query = update.callback_query
    if query is None:
        return
    raw_message = query.message
    if not settings.learning_mode_enabled:
        await query.answer()
        if raw_message is not None and hasattr(raw_message, "reply_text"):
            await cast(Message, raw_message).reply_text("режим обучения отключён")
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
    if slug not in TOPICS_RU:
        await message.reply_text("Неизвестная тема")
        return
    profile = _get_profile(user_data)
    if not await _hydrate(update, context):
        return
    await _start_lesson(message, user_data, context.bot_data, profile, slug)


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
    if not await _hydrate(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    state = get_state(user_data)
    if state is None or not state.awaiting or user_data.get(BUSY_KEY):
        return
    if _rate_limited(user_data, "_answer_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    profile = _get_profile(user_data)
    telegram_id = from_user.id if from_user else None
    user_text = message.text.strip()
    if telegram_id is not None:
        try:
            await add_lesson_log(
                telegram_id,
                0,
                cast(int, user_data.get("learning_module_idx", 0)),
                state.step,
                "user",
                "",
            )
        except (SQLAlchemyError, httpx.HTTPError, RuntimeError) as exc:
            logger.exception("lesson log failed: %s", exc)
            await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
            state.awaiting = True
            set_state(user_data, state)
            return
    state.awaiting = False
    user_data[BUSY_KEY] = True
    set_state(user_data, state)
    try:
        if user_text.lower() == "не знаю":
            feedback = await assistant_chat(
                profile, f"Объясни подробнее: {state.last_step_text}"
            )
        else:
            _correct, feedback = await check_user_answer(
                profile, state.topic, user_text, state.last_step_text or ""
            )
        feedback = format_reply(feedback)
        await message.reply_text(feedback, reply_markup=build_main_keyboard())
        if feedback == BUSY_MESSAGE:
            return
        if telegram_id is not None:
            try:
                await add_lesson_log(
                    telegram_id,
                    0,
                    cast(int, user_data.get("learning_module_idx", 0)),
                    state.step,
                    "assistant",
                    "",
                )
            except (SQLAlchemyError, httpx.HTTPError, RuntimeError) as exc:
                logger.exception("lesson log failed: %s", exc)
                await message.reply_text(
                    BUSY_MESSAGE, reply_markup=build_main_keyboard()
                )
                return
        next_text = await generate_step_text(
            profile, state.topic, state.step + 1, feedback
        )
        if next_text == BUSY_MESSAGE:
            await message.reply_text(next_text, reply_markup=build_main_keyboard())
            return
        next_text = format_reply(next_text)
        await message.reply_text(next_text, reply_markup=build_main_keyboard())
        if telegram_id is not None:
            try:
                await add_lesson_log(
                    telegram_id,
                    0,
                    cast(int, user_data.get("learning_module_idx", 0)),
                    state.step + 1,
                    "assistant",
                    "",
                )
            except (SQLAlchemyError, httpx.HTTPError, RuntimeError) as exc:
                logger.exception("lesson log failed: %s", exc)
                await message.reply_text(
                    BUSY_MESSAGE, reply_markup=build_main_keyboard()
                )
                return
        state.step += 1
        state.last_step_text = next_text
        state.prev_summary = feedback
    finally:
        user_data[BUSY_KEY] = False
        state.awaiting = True
        set_state(user_data, state)
        if from_user is not None:
            await _persist(from_user.id, user_data, context.bot_data)


async def assistant_chat(profile: Mapping[str, str | None], text: str) -> str:
    """Answer a general user question via the learning LLM."""

    system = build_system_prompt(profile)
    user = f"{text[:400]}\n\nОтветь в 2–5 предложениях."
    try:
        return await create_learning_chat_completion(
            task=LLMTask.EXPLAIN_STEP,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=200,
        )
    except (OpenAIError, httpx.HTTPError, RuntimeError) as exc:
        logger.exception("[GPT] assistant chat failed: %s", exc)
        return "сервер занят, попробуйте позже"


async def on_any_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any incoming text either as an answer or a general query."""

    message = update.message
    if message is None or not message.text:
        return
    if not settings.learning_mode_enabled:
        return
    if settings.learning_content_mode != "dynamic":
        return
    if not await _hydrate(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    state = get_state(user_data)
    if state is not None and state.awaiting and state.last_step_text:
        await lesson_answer_handler(update, context)
        raise ApplicationHandlerStop
    profile = _get_profile(user_data)
    reply = await assistant_chat(profile, message.text.strip())
    reply = format_reply(reply)
    await message.reply_text(reply, reply_markup=build_main_keyboard())
    raise ApplicationHandlerStop


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
    if not await _hydrate(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    clear_state(user_data)
    user = update.effective_user
    if user is not None:
        await _persist(user.id, user_data, context.bot_data)
    await message.reply_text(
        f"Сессия {LEARN_BUTTON_TEXT} завершена.", reply_markup=build_main_keyboard()
    )


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the current learning plan."""

    message = update.message
    if message is None:
        return
    if not await _hydrate(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    plan = cast(list[str] | None, user_data.get("learning_plan"))
    if not plan:
        await message.reply_text(
            f"План не найден. Нажмите кнопку {LEARN_BUTTON_TEXT} или команду /learn, чтобы начать.",
            reply_markup=build_main_keyboard(),
        )
        return
    await message.reply_text(pretty_plan(plan), reply_markup=build_main_keyboard())


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Advance to the next step in the learning plan."""

    message = update.message
    if message is None:
        return
    if not await _hydrate(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    plan = cast(list[str] | None, user_data.get("learning_plan"))
    if not plan:
        await message.reply_text(
            f"План не найден. Нажмите кнопку {LEARN_BUTTON_TEXT} или команду /learn, чтобы начать.",
            reply_markup=build_main_keyboard(),
        )
        return
    idx = cast(int, user_data.get("learning_plan_index", 0)) + 1
    if idx >= len(plan):
        await message.reply_text("План завершён.", reply_markup=build_main_keyboard())
    else:
        await message.reply_text(plan[idx], reply_markup=build_main_keyboard())
    user_data["learning_plan_index"] = idx
    user = update.effective_user
    if user is not None:
        await _persist(user.id, user_data, context.bot_data)


__all__ = [
    "curriculum_engine",
    "topics_command",
    "learn_command",
    "lesson_command",
    "lesson_callback",
    "lesson_answer_handler",
    "on_any_text",
    "exit_command",
    "plan_command",
    "skip_command",
]
