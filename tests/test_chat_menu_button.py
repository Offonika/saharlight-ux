"""Tests for ChatMenuButton configuration in bot.main."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import MenuButtonWebApp

from services.bot.main import commands, post_init


@pytest.mark.asyncio
async def test_post_init_sets_chat_menu_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WEBAPP_URL triggers chat menu button setup."""
    monkeypatch.setenv("WEBAPP_URL", "https://app.example")
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot)
    await post_init(app)
    bot.set_my_commands.assert_awaited_once_with(commands)
    bot.set_chat_menu_button.assert_awaited_once()

    button = bot.set_chat_menu_button.call_args.kwargs["menu_button"]
    assert button.web_app.url == "https://app.example/reminders"
    assert button.text == "Menu"



@pytest.mark.asyncio
async def test_post_init_skips_chat_menu_button_without_url(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Missing WEBAPP_URL logs warning and skips setup."""
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot)
    with caplog.at_level(logging.WARNING, logger="services.bot.main"):
        await post_init(app)
    bot.set_chat_menu_button.assert_not_called()
    assert "WEBAPP_URL not configured" in caplog.text
