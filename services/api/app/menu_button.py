"""Configure Telegram chat menu button with WebApp links."""

from __future__ import annotations

from typing import Any

from telegram import MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, ContextTypes, ExtBot, JobQueue

from . import config

DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]


async def post_init(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        DefaultJobQueue,
    ],
) -> None:
    """Set chat menu button to open WebApp if configured."""

    base_url = config.settings.webapp_url
    if not base_url:
        return
    base_url = base_url.rstrip("/")
    button = MenuButtonWebApp("Open", WebAppInfo(base_url))
    await app.bot.set_chat_menu_button(menu_button=button)


__all__ = ["post_init"]
