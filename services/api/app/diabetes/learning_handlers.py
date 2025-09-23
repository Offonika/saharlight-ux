from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Mapping, MutableMapping, TypeAlias, cast

import httpx
import sqlalchemy as sa
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
    MessageHandler,
    filters,
)

from services.api.app import profiles
from services.api.app.config import TOPICS_RU, settings
from services.api.app.ui.keyboard import build_main_keyboard
from services.api.rest_client import AuthRequiredError
from services.api.app.diabetes.models_learning import (
    Lesson,
    LessonProgress,
    ProgressData,
)
from services.api.app.diabetes.services.db import SessionLocal, run_db
from services.api.app.diabetes.services.repository import commit
from .dynamic_tutor import (
    BUSY_MESSAGE,
    check_user_answer,
    generate_step_text,
    sanitize_feedback,
    ensure_single_question,
)
from ..ui.keyboard import ASSISTANT_BUTTON_TEXT
from .learning_onboarding import ensure_overrides, needs_age, needs_level
from .learning_state import LearnState, clear_state, get_state, set_state
from .learning_utils import choose_initial_topic

# Re-export the curriculum engine so tests and callers can patch it easily.
# Including it in ``__all__`` below marks the import as used for the linter.
from . import curriculum_engine as curriculum_engine
from .curriculum_engine import LessonNotFoundError, ProgressNotFoundError
from .prompts import build_system_prompt, build_user_prompt_step, disclaimer
from .llm_router import LLMTask
from .services.gpt_client import (
    choose_model,
    create_learning_chat_completion,
    format_reply,
    make_cache_key,
)
from services.api.app.assistant.repositories.logs import (
    pending_logs,
    safe_add_lesson_log,
)
from services.api.app.diabetes.metrics import step_advance_total
from services.api.app.assistant.repositories import plans as plans_repo
from services.api.app.assistant.repositories.learning_profile import (
    get_learning_profile,
    upsert_learning_profile,
)
from services.api.app.assistant.services import progress_service as progress_repo
from .planner import generate_learning_plan, pretty_plan

if TYPE_CHECKING:
    App: TypeAlias = Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        JobQueue[ContextTypes.DEFAULT_TYPE],
    ]
else:
    App = Application

logger = logging.getLogger(__name__)

PLANS_KEY = "learning_plans"
PROGRESS_KEY = "learning_progress"
BUSY_KEY = "learn_busy"
STEP_GRACE_PERIOD = 5 * 60

RATE_LIMIT_SECONDS = 3.0
RATE_LIMIT_MESSAGE = "⏳ Подождите немного перед следующим запросом."
AUTH_REQUIRED_MESSAGE = AuthRequiredError.MESSAGE
LESSON_NOT_FOUND_MESSAGE = "Учебные материалы недоступны, обратитесь в поддержку."


debug = os.getenv("LEARNING_DEBUG", "0") == "1"


def _sha1(s: str) -> str:
    """Return SHA1 hex digest for ``s``."""

    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _rate_limited(user_data: MutableMapping[str, Any], key: str) -> bool:
    """Return ``True`` if action identified by ``key`` is too frequent."""

    now = time.monotonic()
    last = cast(float | None, user_data.get(key))
    if last is not None and now - last < RATE_LIMIT_SECONDS:
        return True
    user_data[key] = now
    return False


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main persistent keyboard."""

    message = update.effective_message
    if message:
        await message.reply_text("Главное меню:", reply_markup=build_main_keyboard())


async def on_learn_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Proxy button presses to :func:`learn_command`."""

    await learn_command(update, ctx)


def _get_profile(user_data: MutableMapping[str, Any]) -> Mapping[str, str | None]:
    raw = user_data.get("learn_profile_overrides")
    if isinstance(raw, Mapping):
        return raw
    return {}


async def _generate_step_text_logged(
    profile: Mapping[str, str | None],
    topic_slug: str,
    step_idx: int,
    prev_summary: str | None,
    *,
    user_id: int | None,
    plan_id: int | None,
    last_sent_step_id: int | None,
) -> str:
    """Generate step text with optional debug logging."""

    system = build_system_prompt(profile, task=LLMTask.EXPLAIN_STEP)
    user_prompt = build_user_prompt_step(topic_slug, step_idx, prev_summary)
    if debug:
        model = choose_model(LLMTask.EXPLAIN_STEP)
        old_key = make_cache_key(model, system, user_prompt, "", "", "", None, "")
        new_key = make_cache_key(
            model,
            system,
            user_prompt,
            str(user_id) if user_id is not None else "",
            str(plan_id) if plan_id is not None else "",
            topic_slug,
            step_idx,
            "",
        )
        logger.info(
            "learning_debug_before_llm",
            extra={
                "user_id": user_id,
                "plan_id": plan_id,
                "topic_slug": topic_slug,
                "step_idx": step_idx,
                "last_sent_step_id": last_sent_step_id,
                "sys_h": _sha1(system)[:12],
                "usr_h": _sha1(user_prompt)[:12],
                "cache_key_old_preview": _sha1("|".join(old_key))[:12],
                "cache_key_new_preview": _sha1("|".join(new_key))[:12],
            },
        )
    text = await generate_step_text(profile, topic_slug, step_idx, prev_summary)
    if debug:
        logger.info(
            "learning_debug_after_llm",
            extra={
                "pending_step_id": step_idx,
                "reply_preview": text[:120],
            },
        )
    return text


async def _persist(
    user_id: int,
    user_data: MutableMapping[str, Any],
    bot_data: MutableMapping[str, object],
) -> None:
    plans = cast(dict[int, Any], bot_data.setdefault(PLANS_KEY, {}))
    progress = cast(dict[int, ProgressData], bot_data.setdefault(PROGRESS_KEY, {}))
    raw_plan = user_data.get("learning_plan")
    plan: list[str] | None = raw_plan if isinstance(raw_plan, list) else None
    raw_plan_id = user_data.get("learning_plan_id")
    plan_id = raw_plan_id if isinstance(raw_plan_id, int) else None
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
            user_data.pop("learning_plan_id", None)
    state = get_state(user_data)
    if state is not None and plan_id is not None:
        data: ProgressData = {
            "topic": state.topic,
            "module_idx": cast(int, user_data.get("learning_module_idx", 0)),
            "step_idx": state.step,
            "snapshot": state.last_step_text,
            "prev_summary": state.prev_summary,
            "last_sent_step_id": state.last_sent_step_id,
        }
        progress[user_id] = data
        try:
            await progress_repo.upsert_progress(user_id, plan_id, data)
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
        profile = await get_learning_profile(user.id)
    except (
        SQLAlchemyError,
        RuntimeError,
    ) as exc:  # pragma: no cover - logging only
        logger.exception("profile hydrate failed: %s", exc)
        profile = None
    if profile is None:
        overrides = cast(
            Mapping[str, str | None], user_data.get("learn_profile_overrides", {})
        )
        if not user_data.get("learning_profile_backfilled") and (
            overrides.get("age_group") or overrides.get("learning_level")
        ):
            try:
                await upsert_learning_profile(
                    user.id,
                    age_group=overrides.get("age_group"),
                    learning_level=overrides.get("learning_level"),
                )
                user_data["learning_profile_backfilled"] = True
                has_age = overrides.get("age_group") is not None
                has_level = overrides.get("learning_level") is not None
                has_dtype = overrides.get("diabetes_type") is not None
                logger.info(
                    "learning_profile backfilled user_id=%s",
                    user.id,
                    extra={
                        "user_id": user.id,
                        "has_age": has_age,
                        "has_level": has_level,
                        "has_dtype": has_dtype,
                        "branch": "backfill",
                        "reason": "no_profile",
                    },
                )
            except (
                SQLAlchemyError,
                RuntimeError,
            ) as exc:  # pragma: no cover - logging only
                logger.exception("profile backfill failed: %s", exc)
    else:
        overrides = cast(
            MutableMapping[str, str],
            user_data.setdefault("learn_profile_overrides", {}),
        )
        if profile.age_group is not None:
            overrides["age_group"] = profile.age_group
        if profile.learning_level is not None:
            overrides["learning_level"] = profile.learning_level
        if profile.diabetes_type is not None:
            overrides["diabetes_type"] = profile.diabetes_type
        if profile.age_group and profile.learning_level:
            user_data["learning_onboarded"] = True
    if get_state(user_data) is not None:
        return True
    if "learning_plan" in user_data and "learning_plan_index" in user_data:
        return True
    bot_data = cast(MutableMapping[str, Any], context.bot_data)
    plans_map = cast(dict[int, Any], bot_data.setdefault(PLANS_KEY, {}))
    progress_map = cast(dict[int, ProgressData], bot_data.setdefault(PROGRESS_KEY, {}))
    data = progress_map.get(user.id)
    if data is not None and "last_sent_step_id" not in data:
        data["last_sent_step_id"] = None
    raw_plan = plans_map.get(user.id)
    plan: list[str] | None = raw_plan if isinstance(raw_plan, list) else None
    raw_plan_id = user_data.get("learning_plan_id")
    plan_id = raw_plan_id if isinstance(raw_plan_id, int) else None
    if data is None or plan is None or plan_id is None:
        try:
            db_plan = await plans_repo.get_active_plan(user.id)
            if db_plan is None:
                return True
            plan = db_plan.plan_json
            plan_id = db_plan.id
            db_progress = await progress_repo.get_progress(user.id, plan_id)
            if db_progress is None:
                return True
            data = db_progress.progress_json
            if "last_sent_step_id" not in data:
                data["last_sent_step_id"] = None
            plans_map[user.id] = plan
            progress_map[user.id] = data
            user_data["learning_plan_id"] = plan_id
        except (
            SQLAlchemyError,
            RuntimeError,
        ) as exc:  # pragma: no cover - logging only
            logger.exception("hydrate failed: %s", exc)
            return True
    topic = data["topic"]
    module_idx = data["module_idx"]
    step_idx = data["step_idx"]
    snapshot = data["snapshot"]
    prev_summary = data["prev_summary"]
    last_sent_step_id = data["last_sent_step_id"]
    user_data["learning_module_idx"] = module_idx
    user_data["learning_plan"] = plan
    user_data["learning_plan_index"] = step_idx - 1 if step_idx > 0 else 0
    if snapshot is None:
        profile_map = _get_profile(user_data)
        snapshot = await _generate_step_text_logged(
            profile_map,
            topic,
            step_idx,
            prev_summary,
            user_id=user.id,
            plan_id=plan_id,
            last_sent_step_id=last_sent_step_id,
        )
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
            await progress_repo.upsert_progress(user.id, plan_id, data)
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
        last_sent_step_id=last_sent_step_id,
        awaiting=True,
        last_step_at=time.monotonic(),
    )
    set_state(user_data, state)
    return True


async def _static_learn_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Static learning command implementation."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text(f"🚫 {ASSISTANT_BUTTON_TEXT} недоступен.")
        return
    if not await ensure_overrides(update, context):
        return
    model = settings.learning_command_model

    def _list(session: Session) -> list[tuple[str, str]]:
        lessons = session.scalars(
            sa.select(Lesson).filter_by(is_active=True).order_by(Lesson.id)
        ).all()
        return [(lesson.title, lesson.slug) for lesson in lessons]

    lessons = await run_db(_list, sessionmaker=SessionLocal)
    if not lessons:
        logger.info(
            "learn_fallback",
            extra={"content_mode": "static", "branch": "dynamic"},
        )
        await _dynamic_learn_command(update, context)
        return

    titles = "\n".join(f"/lesson {slug} — {title}" for title, slug in lessons)
    await message.reply_text(
        f"{ASSISTANT_BUTTON_TEXT} активирован. Модель: {model}\n\nДоступные уроки:\n{titles}",
        reply_markup=build_main_keyboard(),
    )


async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show an inline keyboard with available learning topics."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    if settings.learning_content_mode == "static":
        await _static_learn_command(update, context)
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


async def _dynamic_learn_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Dynamic learning command implementation."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
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
    try:
        profile_db = await profiles.get_profile_for_user(user.id, context)
    except AuthRequiredError as exc:
        await message.reply_text(str(exc), reply_markup=build_main_keyboard())
        return
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            await message.reply_text(
                AUTH_REQUIRED_MESSAGE, reply_markup=build_main_keyboard()
            )
            return
        logger.exception("Failed to get profile for user %s", user.id)
        profile_db = {}
    except (httpx.HTTPError, RuntimeError):
        logger.exception("Failed to get profile for user %s", user.id)
        profile_db = {}
    overrides = cast(dict[str, str], user_data.get("learn_profile_overrides", {}))
    has_age = "age_group" in overrides or not needs_age(profile_db)
    has_level = "learning_level" in overrides or not needs_level(profile_db)
    asked = "age" if not has_age else "level" if has_age and not has_level else "none"
    logger.info(
        "learn_command",
        extra={
            "user_id": user.id,
            "has_age": has_age,
            "has_level": has_level,
            "asked": asked,
        },
    )
    state = get_state(user_data)
    if state is not None and state.last_step_text:
        sent = await message.reply_text(
            state.last_step_text, reply_markup=build_main_keyboard()
        )
        state.awaiting = True
        state.last_step_at = time.monotonic()
        state.last_sent_step_id = getattr(sent, "message_id", None)
        set_state(user_data, state)
        raw_plan_id = user_data.get("learning_plan_id")
        plan_id = raw_plan_id if isinstance(raw_plan_id, int) else None
        if plan_id is not None:
            progress_map = cast(
                dict[int, ProgressData], context.bot_data.setdefault(PROGRESS_KEY, {})
            )
            data: ProgressData = {
                "topic": state.topic,
                "module_idx": cast(int, user_data.get("learning_module_idx", 0)),
                "step_idx": state.step,
                "snapshot": state.last_step_text,
                "prev_summary": state.prev_summary,
                "last_sent_step_id": state.last_sent_step_id,
            }
            progress_map[user.id] = data
            try:
                await progress_repo.upsert_progress(user.id, plan_id, data)
            except (SQLAlchemyError, RuntimeError) as exc:
                logger.exception("persist progress failed: %s", exc)
        return
    if not await ensure_overrides(update, context):
        return
    profile = _get_profile(user_data)
    slug, _ = choose_initial_topic(profile)
    logger.info("learn_start", extra={"content_mode": "dynamic", "branch": "dynamic"})
    lesson_id: int | None = None
    try:
        progress = await curriculum_engine.start_lesson(user.id, slug)
        lesson_id = progress.lesson_id
        user_data["lesson_id"] = lesson_id
        text, _ = await curriculum_engine.next_step(user.id, lesson_id, profile, None)
    except LessonNotFoundError:
        logger.warning(
            "no_static_lessons; run dynamic",
            extra={"hint": "make load-lessons"},
        )
        text = await _generate_step_text_logged(
            profile,
            slug,
            1,
            None,
            user_id=user.id,
            plan_id=None,
            last_sent_step_id=None,
        )
    except (
        SQLAlchemyError,
        OpenAIError,
        httpx.HTTPError,
        RuntimeError,
    ) as exc:
        logger.exception("lesson start failed: %s", exc)
        user_data.pop("lesson_id", None)
        await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
        return
    if text == BUSY_MESSAGE or not text:
        user_data.pop("lesson_id", None)
        await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
        return
    plan = generate_learning_plan(text)
    user_data["learning_plan"] = plan
    user_data["learning_plan_index"] = 0
    await message.reply_text(
        f"\U0001f5fa План обучения\n{pretty_plan(plan)}",
        reply_markup=build_main_keyboard(),
    )
    text = ensure_single_question(format_reply(plan[0]))
    sent = await message.reply_text(text, reply_markup=build_main_keyboard())
    state = LearnState(
        topic=slug,
        step=1,
        last_step_text=text,
        prev_summary=None,
        last_sent_step_id=getattr(sent, "message_id", None),
        awaiting=True,
        last_step_at=time.monotonic(),
    )
    set_state(user_data, state)
    await _persist(user.id, user_data, context.bot_data)
    raw_plan_id = user_data.get("learning_plan_id")
    plan_id = raw_plan_id if isinstance(raw_plan_id, int) else None
    if plan_id is not None:
        await safe_add_lesson_log(
            user.id,
            plan_id,
            cast(int, user_data.get("learning_module_idx", 0)),
            1,
            "assistant",
            "",
        )


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start learning or display topics depending on configuration."""

    if settings.learning_content_mode == "static":
        await _static_learn_command(update, context)
    else:
        await _dynamic_learn_command(update, context)


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
    logger.info("learn_start", extra={"content_mode": "dynamic", "branch": "dynamic"})
    lesson_id: int | None = None
    try:
        progress = await curriculum_engine.start_lesson(from_user.id, topic_slug)
        lesson_id = progress.lesson_id
        user_data["lesson_id"] = lesson_id
        text, _ = await curriculum_engine.next_step(
            from_user.id, lesson_id, profile, None
        )
    except LessonNotFoundError:
        logger.warning(
            "no_static_lessons; run dynamic",
            extra={"hint": "make load-lessons"},
        )
        text = await _generate_step_text_logged(
            profile,
            topic_slug,
            1,
            None,
            user_id=from_user.id,
            plan_id=None,
            last_sent_step_id=None,
        )
        if text == BUSY_MESSAGE or not text:
            user_data.pop("lesson_id", None)
            await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
            return
        if not text.startswith(disclaimer()):
            text = f"{disclaimer()}\n\n{text}"
    except (
        SQLAlchemyError,
        OpenAIError,
        httpx.HTTPError,
        RuntimeError,
    ) as exc:
        logger.exception("lesson start failed: %s", exc)
        user_data.pop("lesson_id", None)
        await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
        return
    if text == BUSY_MESSAGE or not text:
        user_data.pop("lesson_id", None)
        await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
        return
    plan = generate_learning_plan(text)
    user_data["learning_plan"] = plan
    user_data["learning_plan_index"] = 0
    await message.reply_text(
        f"\U0001f5fa План обучения\n{pretty_plan(plan)}",
        reply_markup=build_main_keyboard(),
    )
    text = ensure_single_question(format_reply(plan[0]))
    sent = await message.reply_text(text, reply_markup=build_main_keyboard())
    state = LearnState(
        topic=topic_slug,
        step=1,
        last_step_text=text,
        prev_summary=None,
        last_sent_step_id=getattr(sent, "message_id", None),
        awaiting=True,
        last_step_at=time.monotonic(),
    )
    set_state(user_data, state)
    await _persist(from_user.id, user_data, bot_data)
    raw_plan_id = user_data.get("learning_plan_id")
    plan_id = raw_plan_id if isinstance(raw_plan_id, int) else None
    if plan_id is not None:
        await safe_add_lesson_log(
            from_user.id,
            plan_id,
            cast(int, user_data.get("learning_module_idx", 0)),
            1,
            "assistant",
            "",
        )


async def _static_lesson_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Static implementation of lesson command."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text(f"🚫 {ASSISTANT_BUTTON_TEXT} недоступен.")
        return
    if not await ensure_overrides(update, context):
        return
    logger.info("lesson_command_start", extra={"user_id": user.id})
    user_data = cast(MutableMapping[str, Any], context.user_data)
    if _rate_limited(user_data, "_lesson_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    lesson_slug: str | None = None
    if context.args:
        lesson_slug = context.args[0]
        user_data["lesson_slug"] = lesson_slug
    else:
        lesson_slug = cast(str | None, user_data.get("lesson_slug"))
    lesson_id = cast(int | None, user_data.get("lesson_id"))
    if lesson_id is None:
        if lesson_slug is None:
            await message.reply_text(
                f"Сначала выберите урок — нажмите кнопку {ASSISTANT_BUTTON_TEXT} или команду /learn"
            )
            return
        progress = await curriculum_engine.start_lesson(user.id, lesson_slug)
        lesson_id = progress.lesson_id
        user_data["lesson_id"] = lesson_id
    try:
        text, completed = await curriculum_engine.next_step(user.id, lesson_id, {})
    except (LessonNotFoundError, ProgressNotFoundError):
        await message.reply_text(LESSON_NOT_FOUND_MESSAGE)
        user_data.pop("lesson_id", None)
        clear_state(user_data)
        return
    if text == BUSY_MESSAGE:
        await message.reply_text(BUSY_MESSAGE)
        user_data.pop("lesson_id", None)
        return
    if text is None and completed:
        await message.reply_text("Урок завершён")
        clear_state(user_data)
    elif text is not None:
        await message.reply_text(text)
        state = get_state(user_data)
        if state is None:
            topic = lesson_slug or ""
            state = LearnState(topic=topic, step=0, awaiting=False)
        state.step += 1
        state.awaiting = False
        state.last_step_text = text
        set_state(user_data, state)
    logger.info(
        "lesson_command_complete",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a lesson by topic slug passed as an argument."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    if settings.learning_content_mode == "static":
        await _static_lesson_command(update, context)
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
            f"Сначала выберите тему — нажмите кнопку {ASSISTANT_BUTTON_TEXT} или команду /learn"
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
        await _static_lesson_command(update, context)
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
        await quiz_answer_handler(update, context)
        return
    if not await _hydrate(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    state = get_state(user_data)
    now = time.monotonic()
    if state is None or user_data.get(BUSY_KEY):
        return
    if not state.awaiting and now - state.last_step_at > STEP_GRACE_PERIOD:
        return
    if _rate_limited(user_data, "_answer_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    profile = _get_profile(user_data)
    raw_plan_id = user_data.get("learning_plan_id")
    plan_id = raw_plan_id if isinstance(raw_plan_id, int) else None
    telegram_id = from_user.id if from_user else None
    user_text = message.text.strip()
    state.awaiting = False
    user_data[BUSY_KEY] = True
    set_state(user_data, state)
    prev_step = state.step
    try:
        if user_text.lower() == "не знаю":
            feedback = await assistant_chat(
                profile, f"Объясни подробнее: {state.last_step_text}"
            )
        else:
            _correct, feedback = await check_user_answer(
                profile,
                state.topic,
                user_text,
                state.last_step_text or "",
            )
        feedback = format_reply(feedback)
        if feedback == BUSY_MESSAGE:
            await message.reply_text(feedback, reply_markup=build_main_keyboard())
            return
        sanitized_feedback = sanitize_feedback(feedback)
        lesson_id = user_data.get("lesson_id")
        try:
            if isinstance(lesson_id, int):
                next_text, _ = await curriculum_engine.next_step(
                    telegram_id or 0,
                    lesson_id,
                    profile,
                    sanitized_feedback,
                )
            else:
                next_text = await _generate_step_text_logged(
                    profile,
                    state.topic,
                    prev_step + 1,
                    sanitized_feedback,
                    user_id=telegram_id,
                    plan_id=plan_id,
                    last_sent_step_id=state.last_sent_step_id,
                )
        except (
            LessonNotFoundError,
            ProgressNotFoundError,
            SQLAlchemyError,
            OpenAIError,
            httpx.HTTPError,
            RuntimeError,
        ) as exc:
            logger.exception("next step failed: %s", exc)
            await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
            user_data.pop("lesson_id", None)
            return
        if next_text == BUSY_MESSAGE or not next_text:
            await message.reply_text(BUSY_MESSAGE, reply_markup=build_main_keyboard())
            return
        next_text = ensure_single_question(format_reply(next_text))
        combined = sanitized_feedback + "\n\n—\n\n" + next_text
        sent = await message.reply_text(combined, reply_markup=build_main_keyboard())
        state.step = prev_step + 1
        state.last_step_text = next_text
        state.prev_summary = sanitized_feedback
        state.last_sent_step_id = getattr(sent, "message_id", None)
        set_state(user_data, state)
        if telegram_id is not None and plan_id is not None:
            data: ProgressData = {
                "topic": state.topic,
                "module_idx": cast(int, user_data.get("learning_module_idx", 0)),
                "step_idx": state.step,
                "snapshot": state.last_step_text,
                "prev_summary": state.prev_summary,
                "last_sent_step_id": state.last_sent_step_id,
            }
            progress_map = cast(
                dict[int, ProgressData],
                context.bot_data.setdefault(PROGRESS_KEY, {}),
            )
            progress_map[telegram_id] = data
            try:
                await progress_repo.upsert_progress(telegram_id, plan_id, data)
            except (SQLAlchemyError, RuntimeError) as exc:
                logger.exception("persist progress failed: %s", exc)
        log_user_ok: bool | None = None
        log_feedback_ok: bool | None = None
        log_next_ok: bool | None = None
        if telegram_id is not None:
            module_idx = cast(int, user_data.get("learning_module_idx", 0))

            async def _record(step_idx: int, role: str) -> bool:
                if plan_id is None:
                    raise RuntimeError("lesson logging requires an active plan")
                return await safe_add_lesson_log(
                    telegram_id,
                    plan_id,
                    module_idx,
                    step_idx,
                    role,
                    "",
                )

            if plan_id is not None:
                log_user_ok = await _record(prev_step, "user")
                log_feedback_ok = await _record(prev_step, "assistant")
                log_next_ok = await _record(state.step, "assistant")

        pending_count = len(pending_logs)
        logger.info(
            "lesson step advance",
            extra={
                "lesson_flow": {
                    "user_id": telegram_id,
                    "step_before": prev_step,
                    "step_after": state.step,
                    "log_user_ok": log_user_ok,
                    "log_feedback_ok": log_feedback_ok,
                    "log_next_ok": log_next_ok,
                    "pending_count": pending_count,
                }
            },
        )
        step_advance_total.inc()
    finally:
        user_data[BUSY_KEY] = False
        state.awaiting = True
        state.last_step_at = time.monotonic()
        set_state(user_data, state)
        if from_user is not None:
            await _persist(from_user.id, user_data, context.bot_data)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle quiz questions and answers for the current lesson."""

    if settings.learning_content_mode != "static":
        return
    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text(f"🚫 {ASSISTANT_BUTTON_TEXT} недоступен.")
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    if _rate_limited(user_data, "_quiz_ts"):
        await message.reply_text(RATE_LIMIT_MESSAGE)
        return
    lesson_id = cast(int | None, user_data.get("lesson_id"))
    if lesson_id is None:
        await message.reply_text("Урок не выбран")
        return
    state = get_state(user_data)
    if context.args:
        try:
            answer = int(context.args[0])
        except ValueError:
            await message.reply_text("Ответ должен быть числом")
            return
        if state is not None:
            state.awaiting = False
            set_state(user_data, state)
        _correct, feedback = await curriculum_engine.check_answer(
            user.id, lesson_id, {}, answer
        )
        sanitized_feedback = sanitize_feedback(feedback)
        try:
            question, completed = await curriculum_engine.next_step(
                user.id, lesson_id, {}
            )
        except (LessonNotFoundError, ProgressNotFoundError):
            await message.reply_text(LESSON_NOT_FOUND_MESSAGE)
            user_data.pop("lesson_id", None)
            clear_state(user_data)
            return
        if question == BUSY_MESSAGE:
            await message.reply_text(BUSY_MESSAGE)
            return
        if question is None and completed:
            await message.reply_text(sanitized_feedback + "\n\n—\n\nОпрос завершён")
            clear_state(user_data)
        elif question is not None:
            question = ensure_single_question(question)
            combined = sanitized_feedback + "\n\n—\n\n" + question
            await message.reply_text(combined)
            if state is None:
                topic = cast(str | None, user_data.get("lesson_slug")) or ""
                state = LearnState(topic=topic, step=0, awaiting=False)
            state.step += 1
            state.awaiting = True
            set_state(user_data, state)
        return
    try:
        question, completed = await curriculum_engine.next_step(user.id, lesson_id, {})
    except (LessonNotFoundError, ProgressNotFoundError):
        await message.reply_text(LESSON_NOT_FOUND_MESSAGE)
        user_data.pop("lesson_id", None)
        clear_state(user_data)
        return
    if question == BUSY_MESSAGE:
        await message.reply_text(BUSY_MESSAGE)
        return
    if question is None and completed:
        await message.reply_text("Опрос завершён")
        clear_state(user_data)
    elif question is not None:
        question = ensure_single_question(question)
        await message.reply_text(question)
        if state is None:
            topic = cast(str | None, user_data.get("lesson_slug")) or ""
            state = LearnState(topic=topic, step=0, awaiting=False)
        state.step += 1
        state.awaiting = True
        set_state(user_data, state)


async def quiz_answer_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Treat plain text as an answer when awaiting a quiz response."""

    if settings.learning_content_mode != "static":
        return
    message = update.message
    user = update.effective_user
    if message is None or user is None or not message.text:
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    state = get_state(user_data)
    if state is None or not state.awaiting:
        return
    lesson_id = cast(int | None, user_data.get("lesson_id"))
    if lesson_id is None:
        clear_state(user_data)
        return
    try:
        answer = int(message.text.strip())
    except ValueError:
        await message.reply_text("Ответ должен быть числом")
        raise ApplicationHandlerStop
    state.awaiting = False
    set_state(user_data, state)
    _correct, feedback = await curriculum_engine.check_answer(
        user.id, lesson_id, {}, answer
    )
    sanitized_feedback = sanitize_feedback(feedback)
    try:
        question, completed = await curriculum_engine.next_step(user.id, lesson_id, {})
    except (LessonNotFoundError, ProgressNotFoundError):
        await message.reply_text(LESSON_NOT_FOUND_MESSAGE)
        user_data.pop("lesson_id", None)
        clear_state(user_data)
        return
    if question == BUSY_MESSAGE:
        await message.reply_text(BUSY_MESSAGE)
        return
    if question is None and completed:
        await message.reply_text(sanitized_feedback + "\n\n—\n\nОпрос завершён")
        clear_state(user_data)
    elif question is not None:
        question = ensure_single_question(question)
        combined = sanitized_feedback + "\n\n—\n\n" + question
        await message.reply_text(combined)
        state.step += 1
        state.awaiting = True
        set_state(user_data, state)
    return


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's current lesson progress."""

    if settings.learning_content_mode != "static":
        return
    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    user_id = user.id

    def _load_progress(
        session: Session, user_id: int
    ) -> tuple[str, int, bool, int | None] | None:
        progress = session.scalars(
            sa.select(LessonProgress)
            .join(Lesson)
            .where(LessonProgress.user_id == user_id)
            .order_by(LessonProgress.id.desc())
        ).first()
        if progress is None:
            return None
        return (
            progress.lesson.title,
            progress.current_step,
            progress.completed,
            progress.quiz_score,
        )

    result = await run_db(_load_progress, user_id, sessionmaker=SessionLocal)
    if result is None:
        await message.reply_text(
            f"Вы ещё не начали обучение. Нажмите кнопку {ASSISTANT_BUTTON_TEXT} или команду /learn, чтобы начать."
        )
        return
    title, current_step, completed, quiz_score = result
    lines = [
        f"📘 {title}",
        f"Шаг: {current_step}",
        f"Завершено: {'да' if completed else 'нет'}",
        f"Баллы викторины: {quiz_score if quiz_score is not None else '—'}",
    ]
    await message.reply_text("\n".join(lines))


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
    now = time.monotonic()
    if (
        state is not None
        and state.last_step_text
        and (state.awaiting or now - state.last_step_at <= STEP_GRACE_PERIOD)
    ):
        await lesson_answer_handler(update, context)
        raise ApplicationHandlerStop
    profile = _get_profile(user_data)
    reply = await assistant_chat(profile, message.text.strip())
    reply = format_reply(reply)
    await message.reply_text(reply, reply_markup=build_main_keyboard())
    raise ApplicationHandlerStop


async def _static_exit_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Static implementation of exit command."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    user_data = cast(dict[str, object], context.user_data)
    lesson_id = cast(int | None, user_data.get("lesson_id"))
    logger.info(
        "exit_command_start", extra={"user_id": user.id, "lesson_id": lesson_id}
    )
    lesson_id = cast(int | None, user_data.pop("lesson_id", None))
    user_data.pop("lesson_slug", None)
    user_data.pop("lesson_step", None)

    if lesson_id is not None:

        def _complete(session: Session, user_id: int, lesson_id: int) -> None:
            progress = session.execute(
                sa.select(LessonProgress).filter_by(
                    user_id=user_id, lesson_id=lesson_id
                )
            ).scalar_one_or_none()
            if progress is not None and not progress.completed:
                progress.completed = True
                commit(session)

        await run_db(_complete, user.id, lesson_id, sessionmaker=SessionLocal)

    await message.reply_text(
        f"Сессия {ASSISTANT_BUTTON_TEXT} завершена.",
        reply_markup=build_main_keyboard(),
    )
    logger.info(
        "exit_command_complete",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit the current lesson and clear stored state."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("режим обучения отключён")
        return
    if settings.learning_content_mode == "static":
        await _static_exit_command(update, context)
        return
    if not await _hydrate(update, context):
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    clear_state(user_data)
    user = update.effective_user
    if user is not None:
        await _persist(user.id, user_data, context.bot_data)
    await message.reply_text(
        f"Сессия {ASSISTANT_BUTTON_TEXT} завершена.", reply_markup=build_main_keyboard()
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
            f"План не найден. Нажмите кнопку {ASSISTANT_BUTTON_TEXT} или команду /learn, чтобы начать.",
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
            f"План не найден. Нажмите кнопку {ASSISTANT_BUTTON_TEXT} или команду /learn, чтобы начать.",
            reply_markup=build_main_keyboard(),
        )
        return
    idx = cast(int, user_data.get("learning_plan_index", 0)) + 1
    completed = idx >= len(plan)
    if completed:
        await message.reply_text("План завершён.", reply_markup=build_main_keyboard())
    else:
        await message.reply_text(plan[idx], reply_markup=build_main_keyboard())
    idx = min(idx, len(plan) - 1)
    user_data["learning_plan_index"] = idx
    user = update.effective_user
    if user is not None and not completed:
        await _persist(user.id, user_data, context.bot_data)


def register_handlers(app: App) -> None:
    """Register learning-related handlers on the application."""

    from .handlers import learning_onboarding as onboarding

    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CommandHandler("topics", topics_command))
    app.add_handler(CommandHandler("lesson", lesson_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CommandHandler("exit", exit_command))
    onboarding.register_handlers(app)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, quiz_answer_handler, block=False
        )
    )
    app.add_handler(CallbackQueryHandler(lesson_callback, pattern="^lesson:"))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, lesson_answer_handler, block=False
        )
    )


__all__ = [
    "curriculum_engine",
    "cmd_menu",
    "on_learn_button",
    "topics_command",
    "learn_command",
    "lesson_command",
    "lesson_callback",
    "lesson_answer_handler",
    "quiz_command",
    "quiz_answer_handler",
    "progress_command",
    "on_any_text",
    "exit_command",
    "plan_command",
    "skip_command",
    "register_handlers",
]
