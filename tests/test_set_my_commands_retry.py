"""Tests for retrying setting bot commands in main.post_init."""

from __future__ import annotations

import importlib
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import NetworkError, RetryAfter


def _reload_main() -> ModuleType:
    import services.bot.main as main

    importlib.reload(main)
    return main


@pytest.mark.asyncio
async def test_post_init_retries_on_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(side_effect=[RetryAfter(1), None]),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())

    await main.post_init(app)

    assert bot.set_my_commands.await_count == 2
    main.asyncio.sleep.assert_awaited_once_with(1)
    main.menu_button_post_init.assert_awaited_once()
    assistant_menu.post_init.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_init_handles_retry_after_and_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(side_effect=[RetryAfter(1), NetworkError("boom")]),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())

    await main.post_init(app)

    assert bot.set_my_commands.await_count == 2
    main.menu_button_post_init.assert_awaited_once()
    assistant_menu.post_init.assert_awaited_once()

