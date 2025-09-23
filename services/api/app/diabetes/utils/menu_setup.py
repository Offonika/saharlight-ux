"""Chat menu configuration helpers for the diabetes bot."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast
from telegram import Bot, MenuButtonDefault

from services.api.app import config

if TYPE_CHECKING:
    from services.api.app.config import Settings

async def setup_chat_menu(bot: Bot, *, settings: Settings | None = None) -> bool:
    """Keep Telegram's default menu button when a WebApp URL is configured.

    Returns ``True`` when a menu button was configured, otherwise ``False``.
    The function safely exits if the bot instance does not expose
    ``set_chat_menu_button`` (for example when using simplified stubs in
    tests).
    """

    active_settings = settings or config.get_settings()
    base_url = active_settings.webapp_url
    if not base_url:
        return False

    set_chat_menu_button: Callable[..., Awaitable[Any]] | None
    set_chat_menu_button = getattr(bot, "set_chat_menu_button", None)
    if not callable(set_chat_menu_button):
        return False

    await cast(Callable[..., Awaitable[Any]], set_chat_menu_button)(
        menu_button=MenuButtonDefault()
    )
    return True


__all__ = ["setup_chat_menu"]
