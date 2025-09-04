from __future__ import annotations

import logging

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from services.api.app.config import settings
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services.db import SessionLocal, run_db

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
        await message.reply_text("Вы ещё не начали обучение. Отправьте /learn чтобы начать.")
        return
    title, current_step, completed, quiz_score = result
    lines = [
        f"📘 {title}",
        f"Шаг: {current_step}",
        f"Завершено: {'да' if completed else 'нет'}",
        f"Баллы викторины: {quiz_score if quiz_score is not None else '—'}",
    ]
    await message.reply_text("\n".join(lines))


__all__ = ["learn_command", "progress_command"]

