"""Configure Telegram chat menu button.

The bot previously replaced Telegram's default menu button with a WebApp link
which hid the built-in command list. To keep the standard menu available we
always reset the button to :class:`telegram.MenuButtonDefault`.
"""

from __future__ import annotations

from typing import Any


from telegram import MenuButtonDefault

from telegram.ext import Application, ContextTypes, ExtBot, JobQueue

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
    """Always restore the default Telegram menu button."""

    await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())


__all__ = ["post_init"]
