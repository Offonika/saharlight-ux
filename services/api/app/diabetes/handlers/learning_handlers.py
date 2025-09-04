from __future__ import annotations

import logging
import time
from typing import Any, MutableMapping, cast

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from services.api.app.config import settings
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services.db import SessionLocal, run_db
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.ui import menu_keyboard

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


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with learning mode status or greeting."""
    message = update.message
    if message is None:
        return
    if not settings.learning_enabled:
        await message.reply_text("🚫 Обучение недоступно.")
        return
    model = settings.learning_command_model
    await message.reply_text(f"🤖 Учебный режим активирован. Модель: {model}")


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start or continue a lesson for the user."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    if not settings.learning_enabled:
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
    text = await curriculum_engine.next_step(user.id, lesson_id)
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
    if not settings.learning_enabled:
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
    if context.args:
        try:
            answer = int(context.args[0])
        except ValueError:
            await message.reply_text("Ответ должен быть числом")
            return
        _correct, feedback = await curriculum_engine.check_answer(
            user.id, lesson_id, answer
        )
        await message.reply_text(feedback)
    question = await curriculum_engine.next_step(user.id, lesson_id)
    if question is None:
        await message.reply_text("Опрос завершён")
    else:
        await message.reply_text(question)


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
        progress = (
            session.query(LessonProgress)
            .join(Lesson)
            .filter(LessonProgress.user_id == user_id)
            .order_by(LessonProgress.id.desc())
            .first()
        )
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
    lesson_id = cast(int | None, user_data.pop("lesson_id", None))
    user_data.pop("lesson_slug", None)
    user_data.pop("lesson_step", None)

    if lesson_id is not None:

        def _complete(session: Session, user_id: int, lesson_id: int) -> None:
            progress = (
                session.query(LessonProgress)
                .filter_by(user_id=user_id, lesson_id=lesson_id)
                .one_or_none()
            )
            if progress is not None and not progress.completed:
                progress.completed = True
                commit(session)

        await run_db(_complete, user.id, lesson_id, sessionmaker=SessionLocal)

    await message.reply_text("Учебная сессия завершена.", reply_markup=menu_keyboard())


__all__ = [
    "learn_command",
    "lesson_command",
    "quiz_command",
    "progress_command",
    "exit_command",
]
