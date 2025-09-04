from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from services.api.app import config

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


__all__ = ["learn_command"]
