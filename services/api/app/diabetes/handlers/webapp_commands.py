from __future__ import annotations

from typing import Awaitable, Callable, Final

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes, ExtBot

from services.api.app import config


_COMMANDS: Final[tuple[tuple[str, str], ...]] = (
    ("history", "История"),
    ("profile", "Профиль"),
    ("subscription", "Подписка"),
    ("reminders", "Напоминания"),
)


def _build_webapp_url(path: str) -> str:
    base_url = config.settings.webapp_url
    if not base_url:
        raise RuntimeError("WEBAPP_URL not configured")
    return base_url.rstrip("/") + path


async def configure_commands(bot: ExtBot[None]) -> None:
    """Configure bot command list for webapp shortcuts."""

    commands = [BotCommand(cmd, desc) for cmd, desc in _COMMANDS]
    await bot.set_my_commands(commands)


def _make_handler(
    path: str, button_text: str
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message is None:
            return
        url = _build_webapp_url(path)
        button = InlineKeyboardButton(button_text, web_app=WebAppInfo(url))
        markup = InlineKeyboardMarkup([[button]])
        await message.reply_text("", reply_markup=markup)

    return handler


history_command = _make_handler("/history", "📊 История")
profile_command = _make_handler("/profile", "📄 Мой профиль")
subscription_command = _make_handler("/subscription", "💳 Подписка")
reminders_command = _make_handler("/api/reminders", "⏰ Напоминания")


__all__ = [
    "configure_commands",
    "history_command",
    "profile_command",
    "subscription_command",
    "reminders_command",
]
