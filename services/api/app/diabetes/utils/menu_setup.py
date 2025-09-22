"""Chat menu configuration for diabetes WebApp shortcuts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urljoin

from telegram import Bot, MenuButtonWebApp, WebAppInfo

from services.api.app import config

if TYPE_CHECKING:
    from services.api.app.config import Settings

_MENU_ITEMS: tuple[tuple[str, str], ...] = (
    ("Profile", "profile"),
    ("Reminders", "reminders"),
    ("History", "history"),
    ("Analytics", "analytics"),
)


def _build_url(base_url: str, path: str) -> str:
    """Join ``base_url`` with ``path`` ensuring a single slash separator."""

    normalized_base = base_url.rstrip("/") + "/"
    normalized_path = path.lstrip("/")
    return urljoin(normalized_base, normalized_path)


async def setup_chat_menu(bot: Bot, *, settings: Settings | None = None) -> bool:
    """Configure the chat menu with WebApp shortcuts when available.

    Returns ``True`` when a custom menu button was configured, otherwise
    ``False``. The function safely exits if the bot instance does not expose
    ``set_chat_menu_button`` (for example when using simplified stubs in tests).
    """

    active_settings = settings or config.get_settings()
    base_url = active_settings.webapp_url
    if not base_url:
        return False

    set_chat_menu_button: Callable[..., Awaitable[Any]] | None
    set_chat_menu_button = getattr(bot, "set_chat_menu_button", None)
    if not callable(set_chat_menu_button):
        return False

    label, path = _MENU_ITEMS[0]
    menu_button = MenuButtonWebApp(
        text=label,
        web_app=WebAppInfo(_build_url(base_url, path)),
    )

    await cast(Callable[..., Awaitable[Any]], set_chat_menu_button)(
        menu_button=menu_button
    )
    return True


__all__ = ["setup_chat_menu"]
