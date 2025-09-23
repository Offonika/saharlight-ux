"""Chat menu configuration helpers for the diabetes bot."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urljoin

from telegram import Bot, MenuButtonDefault

from services.api.app import config

if TYPE_CHECKING:
    from services.api.app.config import Settings


_MENU_ITEMS: tuple[tuple[str, str], ...] = (
    ("Profile", "profile"),
    ("Reminders", "reminders"),
    ("History", "history"),
    ("Analytics", "analytics"),
)

_LAST_CONFIGURED_BASE_URL: str | None = None


def _normalize_base_url(base_url: str) -> str:
    """Normalize ``base_url`` to make change detection stable."""

    return base_url.strip().rstrip("/")


def _build_url(base_url: str, path: str) -> str:
    """Join ``base_url`` with ``path`` ensuring a single slash separator."""

    normalized_base = _normalize_base_url(base_url) + "/"
    normalized_path = path.lstrip("/")
    return urljoin(normalized_base, normalized_path)



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
        _reset_last_configured()
        return False

    normalized_base = _normalize_base_url(base_url)

    set_chat_menu_button: Callable[..., Awaitable[Any]] | None
    set_chat_menu_button = getattr(bot, "set_chat_menu_button", None)
    if not callable(set_chat_menu_button):
        _reset_last_configured()
        return False

    if _LAST_CONFIGURED_BASE_URL == normalized_base:
        return False

    await cast(Callable[..., Awaitable[Any]], set_chat_menu_button)(
        menu_button=MenuButtonDefault()
    )
    _set_last_configured(normalized_base)
    return True


def _reset_last_configured() -> None:
    global _LAST_CONFIGURED_BASE_URL
    _LAST_CONFIGURED_BASE_URL = None


def _set_last_configured(base_url: str) -> None:
    global _LAST_CONFIGURED_BASE_URL
    _LAST_CONFIGURED_BASE_URL = base_url


def is_webapp_menu_active(*, settings: Settings | None = None) -> bool:
    """Return ``True`` when the WebApp menu button matches current settings."""

    if _LAST_CONFIGURED_BASE_URL is None:
        return False

    active_settings = settings or config.get_settings()
    base_url = active_settings.webapp_url
    if not base_url:
        return False

    return _LAST_CONFIGURED_BASE_URL == _normalize_base_url(base_url)


__all__ = ["is_webapp_menu_active", "setup_chat_menu"]
