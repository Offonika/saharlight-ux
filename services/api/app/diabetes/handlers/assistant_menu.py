from __future__ import annotations

"""Inline assistant menu with callback handlers."""

from typing import TYPE_CHECKING, TypeAlias, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from services.api.app.diabetes.utils.ui import (
    BACK_BUTTON_TEXT,
    PROFILE_BUTTON_TEXT,
    REMINDERS_BUTTON_TEXT,
    REPORT_BUTTON_TEXT,
)

__all__ = [
    "assistant_keyboard",
    "show_menu",
    "assistant_callback",
    "ASSISTANT_HANDLER",
]

MENU_LAYOUT: tuple[tuple[InlineKeyboardButton, ...], ...] = (
    (InlineKeyboardButton(PROFILE_BUTTON_TEXT, callback_data="asst:profile"),),
    (InlineKeyboardButton(REMINDERS_BUTTON_TEXT, callback_data="asst:reminders"),),
    (InlineKeyboardButton(REPORT_BUTTON_TEXT, callback_data="asst:report"),),
)

MODE_TEXTS: dict[str, str] = {
    "profile": "Раздел профиля недоступен.",
    "reminders": "Раздел напоминаний недоступен.",
    "report": "Раздел отчётов недоступен.",
}


def assistant_keyboard() -> InlineKeyboardMarkup:
    """Build assistant menu keyboard."""

    return InlineKeyboardMarkup(MENU_LAYOUT)


async def show_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the assistant menu."""

    message = update.effective_message
    if message:
        await message.reply_text("Ассистент:", reply_markup=assistant_keyboard())


def _back_keyboard() -> InlineKeyboardMarkup:
    """Create a back button keyboard."""

    return InlineKeyboardMarkup(
        ((InlineKeyboardButton(BACK_BUTTON_TEXT, callback_data="asst:back"),),)
    )


async def assistant_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle assistant menu callbacks."""

    query = update.callback_query
    if query is None or query.data is None:
        return
    data = query.data
    message = query.message
    await query.answer()
    if data in {"asst:back", "asst:menu"}:
        if message and hasattr(message, "edit_text"):
            await cast(Message, message).edit_text(
                "Ассистент:", reply_markup=assistant_keyboard()
            )
        return
    mode = data.split(":", 1)[1]
    text = MODE_TEXTS.get(mode, "Неизвестная команда.")
    if message and hasattr(message, "edit_text"):
        await cast(Message, message).edit_text(
            text, reply_markup=_back_keyboard()
        )


if TYPE_CHECKING:
    CallbackQueryHandlerT: TypeAlias = CallbackQueryHandler[ContextTypes.DEFAULT_TYPE, object]
else:
    CallbackQueryHandlerT = CallbackQueryHandler

ASSISTANT_HANDLER = CallbackQueryHandlerT(assistant_callback, pattern="^asst:")
