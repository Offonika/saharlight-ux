"""Tests for ChatMenuButton configuration in bot.main."""
from __future__ import annotations

import importlib
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest


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
    """WEBAPP_URL triggers chat menu button setup."""
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

    assert [b.web_app.url for b in menu] == [
        "https://app.example/reminders",
        "https://app.example/history",
        "https://app.example/profile",
        "https://app.example/subscription",
    ]




@pytest.mark.asyncio
async def test_post_init_skips_chat_menu_button_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing WEBAPP_URL skips setup."""
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot)
    await main.post_init(app)
    bot.set_my_commands.assert_awaited_once_with(main.commands)
    bot.set_chat_menu_button.assert_not_called()
