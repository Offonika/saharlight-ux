from __future__ import annotations

import logging
from typing import cast

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from services.api.app import config
from services.api.app.diabetes.handlers import UserData
from services.api.app.diabetes.models_learning import LessonProgress
from services.api.app.diabetes.services import db
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.ui import menu_keyboard

logger = logging.getLogger(__name__)


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with learning mode status or greeting."""
    message = update.message
    if message is None:
        return
    settings = config.get_settings()
    if not settings.learning_mode_enabled:
        await message.reply_text("режим выключен")
        return
    model = settings.learning_model_default
    await message.reply_text(f"🤖 Учебный режим активирован. Модель: {model}")


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit current lesson and reset user state."""
    message = update.effective_message
    if message is None:
        return
    user_data_raw = context.user_data
    if user_data_raw is None:
        context.user_data = {}
        user_data_raw = context.user_data
    user_data = cast(UserData, user_data_raw)
    lesson_id: int | None = user_data.pop("lesson_id", None)
    user_data.pop("lesson_slug", None)
    if lesson_id is not None and update.effective_user is not None:
        user_id = update.effective_user.id

        def _complete(session: Session) -> None:
            progress = (
                session.query(LessonProgress)
                .filter_by(user_id=user_id, lesson_id=lesson_id)
                .one_or_none()
            )
            if progress is not None and not progress.completed:
                progress.completed = True
                commit(session)

        await db.run_db(_complete)
    await message.reply_text("📚 Урок завершён.", reply_markup=menu_keyboard())


__all__ = ["learn_command", "exit_command"]
