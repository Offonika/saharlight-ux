"""Tests for retrying setting bot commands in main.post_init."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from types import MappingProxyType, ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import MenuButtonDefault
from telegram.error import NetworkError, RetryAfter


def _reload_main() -> ModuleType:
    import services.bot.main as main
    import services.api.app.diabetes.utils.menu_setup as menu_setup

    importlib.reload(menu_setup)
    importlib.reload(main)
    return main


@pytest.mark.asyncio
async def test_post_init_retries_on_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(side_effect=[RetryAfter(1), None]),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
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
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
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


@pytest.mark.asyncio
async def test_post_init_skips_recent_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _reload_main()
    now = datetime.now(timezone.utc)
    redis_client = DummyRedis(now.isoformat().encode())
    monkeypatch.setattr(main.redis.Redis, "from_url", lambda url: redis_client)
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
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
    monkeypatch.setattr(main.redis.Redis, "from_url", lambda url: redis_client)
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())

    await main.post_init(app)

    bot.set_my_commands.assert_awaited()
    assert redis_client.set_args is not None
    assert redis_client.set_args[0] == "bot:commands_set_at"
    assert redis_client.set_args[2] >= 86400


@pytest.mark.asyncio
async def test_post_init_with_webapp_url_and_stub_bot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBAPP_URL", "https://web.example/app")
    main = _reload_main()
    bot = SimpleNamespace(set_my_commands=AsyncMock())
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())

    await main.post_init(app)

    bot.set_my_commands.assert_awaited_once_with(main.commands)
    assert not hasattr(bot, "set_chat_menu_button")
    main.menu_button_post_init.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_init_reloads_settings_for_chat_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removing WEBAPP_URL triggers the default menu button configuration."""

    monkeypatch.setenv("WEBAPP_URL", "https://web.example/app")
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}

    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())

    real_menu_post_init = main.menu_button_post_init
    fallback_mock = AsyncMock(side_effect=real_menu_post_init)
    monkeypatch.setattr(main, "menu_button_post_init", fallback_mock)

    await main.post_init(app)
    assert fallback_mock.await_count == 0

    monkeypatch.delenv("WEBAPP_URL", raising=False)

    await main.post_init(app)

    fallback_mock.assert_awaited_once()
    assert bot.set_chat_menu_button.await_count == 2
    last_button = bot.set_chat_menu_button.await_args_list[-1].kwargs["menu_button"]

    assert isinstance(last_button, MenuButtonDefault)
