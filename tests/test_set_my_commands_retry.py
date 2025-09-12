"""Tests for retrying setting bot commands in main.post_init."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import NetworkError, RetryAfter


def _reload_main() -> ModuleType:
    import services.bot.main as main

    importlib.reload(main)
    return main


@pytest.mark.asyncio
async def test_post_init_retries_on_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


class DummyRedis:
    def __init__(self, ts: bytes | None) -> None:
        self._ts = ts
        self.set_args: tuple[str, str, int] | None = None

    async def get(self, key: str) -> bytes | None:
        return self._ts

    async def set(self, key: str, value: str, *, ex: int) -> None:
        self.set_args = (key, value, ex)

    async def close(self) -> None:
        return None


class DummyRedisModule:
    def __init__(self, client: DummyRedis) -> None:
        self._client = client

    def from_url(self, url: str) -> DummyRedis:
        return self._client


@pytest.mark.asyncio
async def test_post_init_skips_recent_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _reload_main()
    now = datetime.now(timezone.utc)
    redis_client = DummyRedis(now.isoformat().encode())
    monkeypatch.setattr(main, "redis", DummyRedisModule(redis_client))
    bot = SimpleNamespace(set_my_commands=AsyncMock())
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())

    await main.post_init(app)

    assert bot.set_my_commands.await_count == 0
    assert redis_client.set_args is None


@pytest.mark.asyncio
async def test_post_init_sets_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _reload_main()
    past = datetime.now(timezone.utc) - timedelta(hours=25)
    redis_client = DummyRedis(past.isoformat().encode())
    monkeypatch.setattr(main, "redis", DummyRedisModule(redis_client))
    bot = SimpleNamespace(set_my_commands=AsyncMock())
    app = SimpleNamespace(bot=bot, job_queue=None, user_data={})
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())

    await main.post_init(app)

    bot.set_my_commands.assert_awaited()
    assert redis_client.set_args is not None
    assert redis_client.set_args[0] == "bot:commands_set_at"
    assert redis_client.set_args[2] >= 86400
