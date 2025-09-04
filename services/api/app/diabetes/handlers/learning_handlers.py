from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from services.api.app.config import settings

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


__all__ = ["learn_command"]
