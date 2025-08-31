"""Configure Telegram chat menu button.

The bot previously replaced Telegram's default menu button with a WebApp link
which hid the built-in command list. To keep the standard menu available we
always reset the button to :class:`telegram.MenuButtonDefault`.
"""

from __future__ import annotations

from telegram import MenuButtonDefault

from telegram.ext import Application, ContextTypes, ExtBot, JobQueue
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    DefaultJobQueue = JobQueue


async def post_init(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        DefaultJobQueue,
    ],
) -> None:
    """Always restore the default Telegram menu button."""

    await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())


__all__ = ["post_init"]
