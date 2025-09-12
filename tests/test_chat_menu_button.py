"""Tests for ChatMenuButton configuration in bot.main."""

from __future__ import annotations

import importlib
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from telegram import MenuButtonDefault
from telegram.error import NetworkError, RetryAfter
from services.api.app.assistant.services import memory_service



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
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://app.example")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    monkeypatch.setattr(memory_service, "get_last_modes", AsyncMock(return_value=[]))
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    await main.post_init(app)
    bot.set_my_commands.assert_awaited_once_with(main.commands)
    bot.set_chat_menu_button.assert_awaited_once()

    menu = bot.set_chat_menu_button.call_args.kwargs["menu_button"]

    assert isinstance(menu, MenuButtonDefault)


@pytest.mark.asyncio
async def test_post_init_skips_chat_menu_button_without_url(
    monkeypatch: pytest.MonkeyPatch,
    ) -> None:
    """Default menu is used when PUBLIC_ORIGIN is missing."""
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("UI_BASE_URL", raising=False)
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    monkeypatch.setattr(memory_service, "get_last_modes", AsyncMock(return_value=[]))
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    await main.post_init(app)
    bot.set_my_commands.assert_awaited_once_with(main.commands)
    bot.set_chat_menu_button.assert_awaited_once()
    button = bot.set_chat_menu_button.call_args.kwargs["menu_button"]
    assert isinstance(button, MenuButtonDefault)


@pytest.mark.asyncio
async def test_post_init_retries_set_my_commands(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Retries once on flood control and logs warning."""
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://app.example")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(side_effect=[RetryAfter(0), None]),
        set_chat_menu_button=AsyncMock(),
    )
    monkeypatch.setattr(memory_service, "get_last_modes", AsyncMock(return_value=[]))
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    with caplog.at_level("WARNING"):
        await main.post_init(app)

    assert bot.set_my_commands.await_count == 2
    warnings = [r for r in caplog.records if "Flood control" in r.getMessage()]
    assert len(warnings) == 1


@pytest.mark.asyncio
async def test_post_init_retry_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Stops retrying if flood control persists or network error occurs."""
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://app.example")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(
            side_effect=[RetryAfter(0), NetworkError("boom")]
        ),
        set_chat_menu_button=AsyncMock(),
    )
    monkeypatch.setattr(memory_service, "get_last_modes", AsyncMock(return_value=[]))
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    with caplog.at_level("WARNING"):
        await main.post_init(app)

    warnings = [r for r in caplog.records if "Flood control" in r.getMessage()]
    assert len(warnings) == 1
