"""Configure Telegram chat menu button.

Whenever a WebApp URL is configured the bot installs a
``MenuButtonWebApp`` pointing to the profile section. Otherwise the standard
Telegram menu button is restored. The helper is idempotent and safely skips
bots that do not expose ``set_chat_menu_button``.
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

    previous_settings = config.get_settings()
    active_settings = config.reload_settings()

    if active_settings.webapp_url != previous_settings.webapp_url:
        menu_setup._reset_last_configured()  # noqa: SLF001

    if await menu_setup.setup_chat_menu(app.bot, settings=active_settings):
        return
    if menu_setup.is_webapp_menu_active(settings=active_settings):
        return

    set_chat_menu_button: Callable[..., Awaitable[Any]] | None
    set_chat_menu_button = getattr(app.bot, "set_chat_menu_button", None)
    if not callable(set_chat_menu_button):
        return

    await cast(Callable[..., Awaitable[Any]], set_chat_menu_button)(
        menu_button=MenuButtonDefault()
    )


__all__ = ["post_init"]
