from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, MutableMapping, TypeAlias, cast

import sqlalchemy as sa
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
    MessageHandler,
    filters,
)

from services.api.app.config import settings
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.learning_state import (
    LearnState,
    clear_state,
    get_state,
    set_state,
)
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services.db import SessionLocal, run_db
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.ui import menu_keyboard
from ...ui.keyboard import build_main_keyboard
from ..learning_onboarding import ensure_overrides

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

RATE_LIMIT_SECONDS = 3.0
RATE_LIMIT_MESSAGE = "⏳ Подождите немного перед следующим запросом."


def _rate_limited(user_data: MutableMapping[str, Any], key: str) -> bool:
    """Return ``True`` if the command with ``key`` is called too often."""

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


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with learning mode status or greeting."""
    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("🚫 Обучение недоступно.")
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
        await message.reply_text(
            "Уроки не найдены. Загрузите уроки: make load-lessons",
            reply_markup=build_main_keyboard(),
        )
        return

    titles = "\n".join(f"/lesson {slug} — {title}" for title, slug in lessons)
    await message.reply_text(
        f"🤖 Учебный режим активирован. Модель: {model}\n\nДоступные уроки:\n{titles}",
        reply_markup=build_main_keyboard(),
    )


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start or continue a lesson for the user."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    logger.info("lesson_command_start", extra={"user_id": user.id})
    if not settings.learning_mode_enabled:
        await message.reply_text("🚫 Обучение недоступно.")
        return
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
            await message.reply_text("Сначала выберите урок командой /learn")
            return
        progress = await curriculum_engine.start_lesson(user.id, lesson_slug)
        lesson_id = progress.lesson_id
        user_data["lesson_id"] = lesson_id
    text, completed = await curriculum_engine.next_step(user.id, lesson_id)
    if text is None and completed:
        await message.reply_text("Урок завершён")
        clear_state(user_data)
    elif text is not None:
        await message.reply_text(text)
        state = get_state(user_data)
        if state is None:
            topic = lesson_slug or ""
            state = LearnState(topic=topic, step=0, awaiting_answer=False)
        state.step += 1
        state.awaiting_answer = False
        state.last_step_text = text
        set_state(user_data, state)
    logger.info(
        "lesson_command_complete",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle quiz questions and answers for the current lesson."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text("🚫 Обучение недоступно.")
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
            state.awaiting_answer = False
            set_state(user_data, state)
        _correct, feedback = await curriculum_engine.check_answer(
            user.id, lesson_id, answer
        )
        await message.reply_text(feedback)
        question, completed = await curriculum_engine.next_step(user.id, lesson_id)
        if question is None and completed:
            await message.reply_text("Опрос завершён")
            clear_state(user_data)
        elif question is not None:
            await message.reply_text(question)
            if state is None:
                topic = cast(str | None, user_data.get("lesson_slug")) or ""
                state = LearnState(topic=topic, step=0, awaiting_answer=False)
            state.step += 1
            state.awaiting_answer = True
            set_state(user_data, state)
        return
    question, completed = await curriculum_engine.next_step(user.id, lesson_id)
    if question is None and completed:
        await message.reply_text("Опрос завершён")
        clear_state(user_data)
    elif question is not None:
        await message.reply_text(question)
        if state is None:
            topic = cast(str | None, user_data.get("lesson_slug")) or ""
            state = LearnState(topic=topic, step=0, awaiting_answer=False)
        state.step += 1
        state.awaiting_answer = True
        set_state(user_data, state)


async def quiz_answer_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Treat plain text as an answer when awaiting a quiz response."""

    message = update.message
    user = update.effective_user
    if message is None or user is None or not message.text:
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    state = get_state(user_data)
    if state is None or not state.awaiting_answer:
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
    state.awaiting_answer = False
    set_state(user_data, state)
    _correct, feedback = await curriculum_engine.check_answer(
        user.id, lesson_id, answer
    )
    await message.reply_text(feedback)
    question, completed = await curriculum_engine.next_step(user.id, lesson_id)
    if question is None and completed:
        await message.reply_text("Опрос завершён")
        clear_state(user_data)
    elif question is not None:
        await message.reply_text(question)
        state.step += 1
        state.awaiting_answer = True
        set_state(user_data, state)
    # Let calling code continue without forcing ApplicationHandlerStop.
    return


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the user's current lesson progress."""
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
            "Вы ещё не начали обучение. Отправьте /learn чтобы начать."
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


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit the current lesson and reset state."""
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

    await message.reply_text("Учебная сессия завершена.", reply_markup=menu_keyboard())
    logger.info(
        "exit_command_complete",
        extra={"user_id": user.id, "lesson_id": lesson_id},
    )


def register_handlers(app: App) -> None:
    """Register learning-related handlers on the application."""

    from . import learning_onboarding as onboarding
    from ..learning_handlers import (
        lesson_answer_handler,
        lesson_callback,
        topics_command as cmd_topics,
    )

    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("lesson", lesson_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("exit", exit_command))
    app.add_handler(CommandHandler("learn_reset", onboarding.learn_reset))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding.onboarding_reply)
    )
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
    "cmd_menu",
    "on_learn_button",
    "learn_command",
    "lesson_command",
    "quiz_command",
    "quiz_answer_handler",
    "progress_command",
    "exit_command",
]
