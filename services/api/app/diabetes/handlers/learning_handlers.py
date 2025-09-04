from __future__ import annotations

import logging
from typing import cast

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from services.api.app.config import settings
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services.db import SessionLocal, run_db
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.ui import menu_keyboard

logger = logging.getLogger(__name__)


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


__all__ = ["learn_command", "progress_command", "exit_command"]
