from __future__ import annotations

import logging
from typing import Any, cast

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from services.api.app.config import settings
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
    if not settings.learning_enabled:
        await message.reply_text("🚫 Обучение недоступно.")
        return
    model = settings.learning_command_model
    await message.reply_text(f"🤖 Учебный режим активирован. Модель: {model}")


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit the current lesson and show the main menu."""
    message = update.message
    if message is None:
        return

    user_data_raw = context.user_data
    if user_data_raw is None:
        return
    user_data = cast(dict[str, Any], user_data_raw)

    lesson_id = cast(int | None, user_data.get("lesson_id"))
    for key in list(user_data.keys()):
        if key.startswith("lesson_"):
            user_data.pop(key, None)

    from_user = message.from_user
    if from_user and lesson_id is not None:
        user_id = from_user.id

        def _finish(session: Session) -> None:
            progress = (
                session.query(LessonProgress)
                .filter_by(user_id=user_id, lesson_id=lesson_id)
                .one_or_none()
            )
            if progress is not None and not progress.completed:
                progress.completed = True
                commit(session)

        await db.run_db(_finish)

    await message.reply_text("✅ Учебный режим завершён.", reply_markup=menu_keyboard())


__all__ = ["learn_command", "exit_command"]
