"""Configure Telegram chat menu button.

The bot always restores Telegram's default chat menu button. Bots that do not
support ``set_chat_menu_button`` are ignored gracefully.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from telegram import MenuButtonDefault
from telegram.ext import Application, ContextTypes, ExtBot, JobQueue

from services.api.app import config
from services.api.app.diabetes.utils import menu_setup

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
    """Configure the chat menu, falling back to Telegram's default button."""

    active_settings = config.reload_settings()

    if await menu_setup.setup_chat_menu(app.bot, settings=active_settings):
        return

    set_chat_menu_button: Callable[..., Awaitable[Any]] | None
    set_chat_menu_button = getattr(app.bot, "set_chat_menu_button", None)
    if not callable(set_chat_menu_button):
        return

    await cast(Callable[..., Awaitable[Any]], set_chat_menu_button)(
        menu_button=MenuButtonDefault()
    )


__all__ = ["post_init"]
