# file: diabetes/handlers/webapp_openers.py
"""Helpers to open external WebApp pages via inline buttons."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from services.api.app import config


async def _open_webapp(update: Update, path: str, text: str) -> None:
    message = update.message
    if message is None:
        return
    base_url = config.settings.webapp_url
    if not base_url:
        await message.reply_text("WebApp не настроен.")
        return
    url = f"{base_url.rstrip('/')}{path}"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text, web_app=WebAppInfo(url))]]
    )
    await message.reply_text("Откройте WebApp:", reply_markup=keyboard)


async def open_history_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a button to open the history WebApp page."""
    await _open_webapp(update, "/history", "📊 История")


async def open_profile_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a button to open the profile WebApp page."""
    await _open_webapp(update, "/profile", "📄 Мой профиль")


async def open_subscription_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a button to open the subscription WebApp page."""
    await _open_webapp(update, "/subscription", "💎 Подписка")


async def open_reminders_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a button to open the reminders WebApp page."""
    await _open_webapp(update, "/reminders", "⏰ Напоминания")


__all__ = [
    "open_history_webapp",
    "open_profile_webapp",
    "open_subscription_webapp",
    "open_reminders_webapp",
]
