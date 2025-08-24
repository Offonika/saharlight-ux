"""Tests for ChatMenuButton configuration in bot.main."""

from __future__ import annotations

import importlib
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from telegram import MenuButtonDefault


def _reload_main() -> ModuleType:
    import services.api.app.config as config
    import services.api.app.menu_button as menu_button
    import services.bot.main as main

    importlib.reload(config)
    importlib.reload(menu_button)
    importlib.reload(main)
    return main


@pytest.mark.asyncio
async def test_post_init_sets_chat_menu_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chat menu button is always set to default."""
    monkeypatch.setenv("WEBAPP_URL", "https://app.example")
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot)
    await main.post_init(app)
    bot.set_my_commands.assert_awaited_once_with(main.commands)
    bot.set_chat_menu_button.assert_awaited_once()

    menu = bot.set_chat_menu_button.call_args.kwargs["menu_button"]

    assert isinstance(menu, MenuButtonDefault)


@pytest.mark.asyncio
async def test_post_init_skips_chat_menu_button_without_url(
    monkeypatch: pytest.MonkeyPatch,
    ) -> None:
    """Default menu is used when WEBAPP_URL is missing."""
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot)
    await main.post_init(app)
    bot.set_my_commands.assert_awaited_once_with(main.commands)
    bot.set_chat_menu_button.assert_awaited_once()
    button = bot.set_chat_menu_button.call_args.kwargs["menu_button"]
    assert isinstance(button, MenuButtonDefault)
