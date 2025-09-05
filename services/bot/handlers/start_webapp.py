from __future__ import annotations

import logging
import os
from typing import TypeAlias

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

CommandHandlerT: TypeAlias = CommandHandler[ContextTypes.DEFAULT_TYPE, object]


def build_start_handler() -> CommandHandlerT:
    """Return a ``/start`` handler that links to the WebApp onboarding."""

    ui_base_url = os.getenv("UI_BASE_URL", "/ui")
    if ui_base_url.startswith("/"):
        public_origin = os.getenv("PUBLIC_ORIGIN", "")
        ui_base_url = f"{public_origin.rstrip('/')}{ui_base_url}"

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
