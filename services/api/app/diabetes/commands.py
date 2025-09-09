from __future__ import annotations

import asyncio
import logging
from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

from .learning_handlers import learn_command, topics_command
from .handlers.onboarding_handlers import reset_onboarding as _reset_onboarding
from ..ui.keyboard import LEARN_BUTTON_TEXT
from .assistant_state import reset as _reset_assistant
from ..assistant.services.memory_service import clear_memory as _clear_memory

logger = logging.getLogger(__name__)

HELP_TEXT = "\n".join(
    [
        "Доступные команды:",
        "/start - начать работу с ботом",
        "/help - краткая справка",
        f"нажмите кнопку {LEARN_BUTTON_TEXT} или команду /learn - режим обучения",
        "/topics - список тем",
        "/reset_onboarding - сбросить мастер настройки",
        "/trial - Включить trial",
        "/upgrade - Оформить PRO",
        "",
        "Для работы с WebApp откройте меню и выберите нужную кнопку.",
    ]
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a brief help message about bot commands and WebApp."""

    message = update.message
    if message:
        await message.reply_text(HELP_TEXT)


async def reset_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Warn user and reset onboarding state on confirmation."""

    message = update.effective_message
    user = getattr(update, "effective_user", None)
    if message is None or user is None:
        return

    user_data = cast(dict[str, object], context.user_data)
    task = user_data.pop("_onb_reset_task", None)
    if user_data.pop("_onb_reset_confirm", False):
        if isinstance(task, asyncio.Task):
            task.cancel()
        await _reset_onboarding(update, context)
        return

    async def _reset_timeout() -> None:
        await asyncio.sleep(45)
        user_data.pop("_onb_reset_confirm", None)
        user_data.pop("_onb_reset_task", None)
        try:
            await message.reply_text(
                "⏱ Сброс онбординга не подтверждён. Отправьте /reset_onboarding снова.",
            )
        except Exception:
            pass

    user_data["_onb_reset_confirm"] = True
    user_data["_onb_reset_task"] = asyncio.create_task(_reset_timeout())
    await message.reply_text(
        "⚠️ Это сбросит прогресс онбординга. Профиль и напоминания не затронутся.\n"
        "Отправьте /reset_onboarding ещё раз для подтверждения.",
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear assistant conversation history and summary."""

    message = update.effective_message
    user = getattr(update, "effective_user", None)
    if message is None:
        return
    user_data = cast(dict[str, object], context.user_data)
    _reset_assistant(user_data)
    if user is not None:
        await _clear_memory(user.id)
    await message.reply_text("История очищена.")


__all__ = [
    "help_command",
    "reset_onboarding",
    "reset_command",
    "learn_command",
    "topics_command",
]
