
from __future__ import annotations

"""Helper handlers that open various WebApp sections.

These functions send an inline button that opens the corresponding WebApp
section when pressed. They rely on :func:`build_webapp_url` to construct
absolute URLs based on the ``WEBAPP_URL`` setting.
"""


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes


from .reminder_handlers import build_webapp_url


async def _open(update: Update, path: str, text: str) -> None:
    """Send a single button opening ``path`` in the WebApp."""
    message = update.effective_message
    if message is None:
        return
    url = build_webapp_url(path)
    button = InlineKeyboardButton(text, web_app=WebAppInfo(url))
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[button]]))


async def open_history_webapp(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Open the history WebApp page."""
    await _open(update, "/history", "📊 История")


async def open_profile_webapp(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Open the profile WebApp page."""
    await _open(update, "/profile", "📄 Мой профиль")


async def open_subscription_webapp(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Open the subscription WebApp page."""
    await _open(update, "/subscription", "💳 Подписка")


async def open_reminders_webapp(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Open the reminders WebApp page."""
    await _open(update, "/api/reminders", "⏰ Напоминания")
