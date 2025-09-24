"""Chat menu configuration helpers for the diabetes bot."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

from telegram import Bot, MenuButtonDefault

if TYPE_CHECKING:
    from services.api.app.config import Settings


async def setup_chat_menu(bot: Bot, *, settings: Settings | None = None) -> bool:
    """Ensure Telegram's chat menu uses the default button.

    ``settings`` is accepted for API compatibility but ignored. The helper
    returns ``True`` when the bot exposes ``set_chat_menu_button`` and the
    default button was configured. Bots without such support are ignored
    gracefully and result in ``False``.
    """

    _ = settings  # explicitly unused to keep signature stable

    set_chat_menu_button: Callable[..., Awaitable[Any]] | None
    set_chat_menu_button = getattr(bot, "set_chat_menu_button", None)
    if not callable(set_chat_menu_button):
        return False

    await cast(Callable[..., Awaitable[Any]], set_chat_menu_button)(
        menu_button=MenuButtonDefault()
    )
    return True


__all__ = ["setup_chat_menu"]
