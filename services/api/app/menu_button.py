"""Configure Telegram chat menu button with WebApp links."""

from __future__ import annotations

from typing import Any


from telegram import (
    MenuButton,
    MenuButtonDefault,
    MenuButtonWebApp,
    WebAppInfo,
)

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

    """Set chat menu buttons to open WebApp sections if configured.


    Falls back to ``MenuButtonDefault`` when WebApp URLs are disabled.
    """

    base_url = config.get_webapp_url()
    if not base_url:
        await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        return

    buttons: list[MenuButtonWebApp] = [
        MenuButtonWebApp("Reminders", WebAppInfo(f"{base_url}/reminders")),
        MenuButtonWebApp("Stats", WebAppInfo(f"{base_url}/history")),
        MenuButtonWebApp("Profile", WebAppInfo(f"{base_url}/profile")),
        MenuButtonWebApp("Billing", WebAppInfo(f"{base_url}/subscription")),
    ]
    await app.bot.set_chat_menu_button(menu_button=cast(MenuButton, buttons))



__all__ = ["post_init"]
