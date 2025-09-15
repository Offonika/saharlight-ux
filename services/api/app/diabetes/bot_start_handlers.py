"""Handlers for the ``/start`` command that launch the WebApp onboarding."""

from __future__ import annotations

from typing import TypeAlias

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CommandHandler, ContextTypes

from services.api.app.utils import choose_variant


CommandHandlerT: TypeAlias = CommandHandler[ContextTypes.DEFAULT_TYPE, object]


def build_start_handler(ui_base_url: str) -> CommandHandlerT:
    """Return a /start handler with WebApp onboarding buttons.

    The handler performs a simple A/B test: users are deterministically split
    into two groups based on their Telegram ``user_id``.  Variant ``A`` shows
    the profile button first, while variant ``B`` shows the reminders button
    first.  The chosen variant is also propagated to the WebApp via a query
    parameter so that subsequent analytics events can be attributed correctly.
    """

    async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        user_id = user.id if user is not None else 0
        variant = choose_variant(user_id)

        profile_url = (
            f"{ui_base_url.rstrip('/')}/profile?flow=onboarding&step=profile&variant={variant}"
        )
        reminders_url = (
            f"{ui_base_url.rstrip('/')}/reminders?flow=onboarding&step=reminders&variant={variant}"
        )

        buttons = [
            InlineKeyboardButton("🧾 Открыть профиль", web_app=WebAppInfo(url=profile_url)),
            InlineKeyboardButton(
                "⏰ Открыть напоминания", web_app=WebAppInfo(url=reminders_url)
            ),
        ]

        if variant == "B":
            buttons = buttons[::-1]

        kb = InlineKeyboardMarkup([[btn] for btn in buttons])

        user_data = getattr(context, "user_data", {})
        text = "👋 Добро пожаловать! Быстрая настройка в приложении:"
        if not isinstance(user_data, dict) or "tg_init_data" not in user_data:
            text = "⚠️ Откройте приложение по кнопке ниже"

        if update.message:
            await update.message.reply_text(text, reply_markup=kb)

    return CommandHandler("start", _start)
