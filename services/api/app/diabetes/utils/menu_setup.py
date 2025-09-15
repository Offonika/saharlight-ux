"""Chat menu configuration for diabetes WebApp shortcuts."""

from __future__ import annotations

from urllib.parse import urljoin

from typing import cast

from telegram import Bot, MenuButton, MenuButtonWebApp, WebAppInfo

from services.api.app import config

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


async def setup_chat_menu(bot: Bot) -> None:
    """Configure the chat menu with WebApp shortcuts when available."""

    settings = config.get_settings()
    base_url = settings.webapp_url
    if not base_url:
        return

    buttons = [
        MenuButtonWebApp(text=label, web_app=WebAppInfo(_build_url(base_url, path)))
        for label, path in _MENU_ITEMS
    ]

    await bot.set_chat_menu_button(menu_button=cast(MenuButton, buttons))


__all__ = ["setup_chat_menu"]
