"""Handlers for the interactive learning mode.

The module implements a very small set of asynchronous telegram handlers used in
unit tests. They expose a primitive learning flow built around the
``curriculum_engine`` helpers. Real logic in the project is considerably more
feature rich, however for tests we only need the simplified behaviour defined
below.
"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from typing import Any, MutableMapping, cast

from services.api.app.config import settings
from . import curriculum_engine
from .models_learning import Lesson, LessonProgress
from .services import db

logger = logging.getLogger(__name__)

# Shared message when the learning mode is disabled
DISABLED_TEXT = "Учебный режим выключен"


async def _fetch_active_lessons() -> list[Lesson]:
    """Return active lessons from the database."""

    def _query(session: Session) -> list[Lesson]:
        return (
            session.query(Lesson).filter_by(is_active=True).order_by(Lesson.id).all()
        )

    return await db.run_db(_query)


async def _fetch_progress(
    user_id: int, lesson_id: int
) -> tuple[LessonProgress | None, Lesson | None]:
    """Return progress and related lesson for a user."""

    def _query(session: Session) -> tuple[LessonProgress | None, Lesson | None]:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=user_id, lesson_id=lesson_id)
            .one_or_none()
        )
        lesson = session.query(Lesson).filter_by(id=lesson_id).one_or_none()
        return progress, lesson

    return await db.run_db(_query)


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available lessons using an inline keyboard."""

    message = update.message
    if message is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text(DISABLED_TEXT)
        return
    lessons = await _fetch_active_lessons()
    if not lessons:
        await message.reply_text("Нет активных уроков")
        return
    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(lesson.title, callback_data=lesson.slug)] for lesson in lessons
    ]
    await message.reply_text(
        "Выберите урок:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start or continue a lesson for the user."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text(DISABLED_TEXT)
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    lesson_slug: str | None = None
    if context.args:
        lesson_slug = context.args[0]
        user_data["lesson_slug"] = lesson_slug
    else:
        lesson_slug = user_data.get("lesson_slug")
    lesson_id = user_data.get("lesson_id")
    if lesson_id is None:
        if lesson_slug is None:
            await message.reply_text("Сначала выберите урок командой /learn")
            return
        started = await curriculum_engine.start_lesson(user.id, lesson_slug)
        lesson_id = started.lesson_id
        user_data["lesson_id"] = lesson_id
    else:
        lesson_id = int(lesson_id)
        progress, lesson = await _fetch_progress(user.id, lesson_id)
        if progress is None or lesson is None:
            await message.reply_text("Урок не найден")
            return
    text = await curriculum_engine.next_step(user.id, int(lesson_id))
    if text is None:
        await message.reply_text("Урок завершён")
    else:
        await message.reply_text(text)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle quiz questions and answers for the current lesson."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text(DISABLED_TEXT)
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    lesson_id = user_data.get("lesson_id")
    if lesson_id is None:
        await message.reply_text("Урок не выбран")
        return
    if context.args:
        try:
            answer = int(context.args[0])
        except ValueError:
            await message.reply_text("Ответ должен быть числом")
            return
        _correct, feedback = await curriculum_engine.check_answer(
            user.id, int(lesson_id), answer
        )
        await message.reply_text(feedback)
    question = await curriculum_engine.next_step(user.id, int(lesson_id))
    if question is None:
        await message.reply_text("Опрос завершён")
    else:
        await message.reply_text(question)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display current progress for the user."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    if not settings.learning_mode_enabled:
        await message.reply_text(DISABLED_TEXT)
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    lesson_id = user_data.get("lesson_id")
    if lesson_id is None:
        await message.reply_text("Урок не выбран")
        return
    lesson_id = int(lesson_id)
    progress, lesson = await _fetch_progress(user.id, lesson_id)
    if progress is None or lesson is None:
        await message.reply_text("Урок не найден")
        return
    score = progress.quiz_score or 0
    await message.reply_text(
        f"Урок: {lesson.title}\nШаг: {progress.current_step}\nБаллы: {score}"
    )


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit learning mode and clear user state."""

    message = update.message
    if message is None:
        return
    user_data = cast(MutableMapping[str, Any], context.user_data)
    user_data.clear()
    if not settings.learning_mode_enabled:
        await message.reply_text(DISABLED_TEXT)
    else:
        await message.reply_text("Вы вышли из учебного режима")


__all__ = [
    "learn_command",
    "lesson_command",
    "quiz_command",
    "progress_command",
    "exit_command",
]
