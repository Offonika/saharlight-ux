"""Helpers for configuring bot commands."""

from typing import Any

from telegram import BotCommand
from telegram.ext import Application, ContextTypes, ExtBot, JobQueue

DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]
DefaultApplication = Application[
    ExtBot[None],
    ContextTypes.DEFAULT_TYPE,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    DefaultJobQueue,
]

COMMANDS: list[BotCommand] = [
    BotCommand("history", "📊 История"),
    BotCommand("profile", "👤 Профиль"),
    BotCommand("subscription", "⭐️ Подписка"),
    BotCommand("reminders", "⏰ Напоминания"),
    BotCommand("report", "📈 Отчёт"),
    BotCommand("help", "ℹ️ Помощь"),
]


async def configure_commands(app: DefaultApplication) -> None:
    """Register default bot commands."""
    await app.bot.set_my_commands(COMMANDS)


__all__ = ["COMMANDS", "configure_commands"]
