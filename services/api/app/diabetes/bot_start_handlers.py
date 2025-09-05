from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CommandHandler, ContextTypes
from typing import TypeAlias


CommandHandlerT: TypeAlias = CommandHandler[ContextTypes.DEFAULT_TYPE, object]


def build_start_handler(ui_base_url: str) -> CommandHandlerT:
    """Return a /start handler with WebApp onboarding buttons."""

    async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        profile_url = (
            f"{ui_base_url.rstrip('/')}/profile?flow=onboarding&step=profile"
        )
        reminders_url = (
            f"{ui_base_url.rstrip('/')}/reminders?flow=onboarding&step=reminders"
        )
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🧾 Открыть профиль", web_app=WebAppInfo(url=profile_url)
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⏰ Открыть напоминания",
                        web_app=WebAppInfo(url=reminders_url),
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
