from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from services.api.app import config

logger = logging.getLogger(__name__)


async def _is_enabled(update: Update) -> bool:
    """Return ``True`` if learning mode is enabled and message exists."""
    message = update.message
    if message is None:
        return False
    settings = config.get_settings()
    if not settings.learning_mode_enabled:
        await message.reply_text("режим выключен")
        return False
    return True


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/lesson`` command."""
    if not await _is_enabled(update):
        return
    message = update.message
    if message:
        await message.reply_text("📘 Урок начат.")


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/quiz`` command."""
    if not await _is_enabled(update):
        return
    message = update.message
    if message:
        await message.reply_text("📝 Викторина началась.")


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/progress`` command."""
    if not await _is_enabled(update):
        return
    message = update.message
    if message:
        await message.reply_text("📈 Прогресс недоступен.")


async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ``/exit`` command."""
    if not await _is_enabled(update):
        return
    message = update.message
    if message:
        await message.reply_text("🚪 Выход из режима обучения.")


__all__ = [
    "lesson_command",
    "quiz_command",
    "progress_command",
    "exit_command",
]
