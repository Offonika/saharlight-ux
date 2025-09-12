from __future__ import annotations

import asyncio
import logging
from typing import cast

import telegram
from telegram import Update
from telegram.ext import ContextTypes

from .learning_handlers import learn_command, topics_command
from .handlers.onboarding_handlers import reset_onboarding as _reset_onboarding
from ..ui.keyboard import LEARN_BUTTON_TEXT
from .assistant_state import reset as _reset_assistant
from .handlers.registration import MODE_DISCLAIMED_KEY
from ..assistant.services.memory_service import clear_memory as _clear_memory
from services.api.app.config import settings

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
            try:
                await task
            except asyncio.CancelledError:
                pass
        await _reset_onboarding(update, context)
        return

    async def _reset_timeout() -> None:
        try:
            await asyncio.sleep(45)
            user_data.pop("_onb_reset_confirm", None)
            user_data.pop("_onb_reset_task", None)
            try:
                await message.reply_text(
                    "⏱ Сброс онбординга не подтверждён. Отправьте /reset_onboarding снова.",
                )
            except telegram.error.TelegramError as exc:
                logger.exception(
                    "Failed to notify about onboarding reset timeout: %s",
                    exc,
                )
        except asyncio.CancelledError:
            raise
        except (telegram.error.TelegramError, RuntimeError) as exc:
            # Swallow known Telegram/runtime errors: they are logged to avoid double
            # reporting and the task shouldn't fail because of them.
            logger.exception("Reset onboarding timeout task failed: %s", exc)
        except Exception as exc:
            logger.exception("Reset onboarding timeout task failed: %s", exc)
            raise

    user_data["_onb_reset_confirm"] = True
    task = asyncio.create_task(_reset_timeout())

    def _log_timeout_failure(t: asyncio.Task[None]) -> None:
        try:
            exc = t.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.exception(
                "Reset onboarding timeout task failed",
                exc_info=exc,
            )

    add_done_callback = getattr(task, "add_done_callback", None)
    if callable(add_done_callback):
        add_done_callback(_log_timeout_failure)

    user_data["_onb_reset_task"] = task
    try:
        await message.reply_text(
            "⚠️ Это сбросит прогресс онбординга. Профиль и напоминания не"
            " затронутся.\n"
            "Отправьте /reset_onboarding ещё раз для подтверждения.",
        )
    except telegram.error.TelegramError as exc:
        logger.exception("Failed to send onboarding reset warning: %s", exc)
        try:
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=(
                    "Не удалось отправить предупреждение о сбросе. Попробуйте снова."
                ),
            )
        except telegram.error.TelegramError as exc2:
            logger.exception(
                "Failed to notify user about onboarding reset warning failure: %s",
                exc2,
            )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear assistant conversation history and summary."""

    message = update.effective_message
    user = getattr(update, "effective_user", None)
    if message is None or not settings.assistant_mode_enabled:
        return
    user_data = cast(dict[str, object], context.user_data)
    _reset_assistant(user_data)
    user_data.pop(MODE_DISCLAIMED_KEY, None)
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
