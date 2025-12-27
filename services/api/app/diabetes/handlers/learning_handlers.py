from __future__ import annotations

import logging

from sqlalchemy.orm import Session, joinedload
from telegram import Update
from telegram.ext import ContextTypes

from ..models_learning import LessonProgress
from ..services import db

logger = logging.getLogger(__name__)


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display learning progress for the user."""
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    def _fetch(session: Session) -> list[LessonProgress]:
        return (
            session.query(LessonProgress)
            .options(joinedload(LessonProgress.lesson))
            .filter_by(user_id=user.id)
            .all()
        )

    progresses = await db.run_db(_fetch)
    if not progresses:
        await message.reply_text("Прогресс не найден. Пройдите /learn.")
        return

    cards: list[str] = []
    for progress in progresses:
        score = progress.quiz_score if progress.quiz_score is not None else "-"
        cards.append(
            f"{progress.lesson.title}\n"
            f"current_step: {progress.current_step}\n"
            f"completed: {progress.completed}\n"
            f"quiz_score: {score}"
        )

    await message.reply_text("\n\n".join(cards))


__all__ = ["progress_command"]
