from __future__ import annotations

import logging
from typing import TypeAlias

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

CommandHandlerT: TypeAlias = CommandHandler[ContextTypes.DEFAULT_TYPE, object]


def build_start_handler(ui_base_url: str) -> CommandHandlerT:
    """Return a ``/start`` handler that links to the WebApp onboarding."""

    async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        profile_url = f"{ui_base_url.rstrip('/')}/profile?flow=onboarding&step=profile"
        reminders_url = f"{ui_base_url.rstrip('/')}/reminders?flow=onboarding&step=reminders"

        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🧾 Открыть профиль", web_app=WebAppInfo(profile_url))],
                [
                    InlineKeyboardButton(
                        "⏰ Открыть напоминания", web_app=WebAppInfo(reminders_url)
                    )
                ],
            ]
        )

        if update.message:
            await update.message.reply_text(
                "👋 Добро пожаловать! Быстрая настройка в приложении:",
                reply_markup=kb,
            )

    return CommandHandlerT("start", _start)


__all__ = ["build_start_handler"]
