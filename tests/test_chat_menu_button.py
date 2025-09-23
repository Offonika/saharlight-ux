"""Tests for ChatMenuButton configuration in bot.main."""

from __future__ import annotations

import importlib
import logging
from types import MappingProxyType, ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import MenuButtonDefault
from telegram.error import NetworkError, RetryAfter

from services.api.app.assistant.services import memory_service



def _reload_main() -> ModuleType:
    import services.api.app.config as config
    import services.api.app.diabetes.utils.menu_setup as menu_setup
    import services.api.app.menu_button as menu_button
    import services.bot.main as main

    importlib.reload(config)
    importlib.reload(menu_setup)
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
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
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
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
    await main.post_init(app)
    bot.set_my_commands.assert_awaited_once_with(main.commands)
    bot.set_chat_menu_button.assert_awaited_once()
    button = bot.set_chat_menu_button.call_args.kwargs["menu_button"]
    assert isinstance(button, MenuButtonDefault)


@pytest.mark.asyncio
async def test_post_init_warns_and_retries_on_retry_after(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retry setting bot commands once and log a warning."""
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(side_effect=[RetryAfter(1), None]),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())

    with caplog.at_level(logging.WARNING):
        await main.post_init(app)

    assert bot.set_my_commands.await_count == 2
    main.asyncio.sleep.assert_awaited_once_with(1)
    warnings = [r for r in caplog.records if "Flood control" in r.message]
    assert len(warnings) == 1


@pytest.mark.asyncio
async def test_post_init_warns_when_retry_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log warnings if retrying to set commands fails again."""
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(
            side_effect=[RetryAfter(1), NetworkError("boom")]
        ),
    )
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())
    monkeypatch.setattr(main.asyncio, "sleep", AsyncMock())

    with caplog.at_level(logging.WARNING):
        await main.post_init(app)

    assert bot.set_my_commands.await_count == 2
    warnings = [r for r in caplog.records if "Flood control" in r.message]
    assert len(warnings) == 2


@pytest.mark.asyncio
async def test_post_init_configures_menu_button_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    """Custom WebApp button is refreshed only when the URL changes."""


    monkeypatch.setenv("WEBAPP_URL", "https://web.example/app")
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )
    monkeypatch.setattr(memory_service, "get_last_modes", AsyncMock(return_value=[]))
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}

    await main.post_init(app)
    bot.set_my_commands.assert_awaited_once_with(main.commands)
    assert bot.set_chat_menu_button.await_count == 1
    button = bot.set_chat_menu_button.call_args.kwargs["menu_button"]

    assert isinstance(button, MenuButtonWebApp)
    assert button.text == "Profile"
    assert button.web_app.url == "https://web.example/app/profile"

    await main.post_init(app)
    assert bot.set_chat_menu_button.await_count == 1
    main.menu_button_post_init.assert_not_awaited()

    monkeypatch.setenv("WEBAPP_URL", "https://web.example/alt")

    await main.post_init(app)
    assert bot.set_chat_menu_button.await_count == 2
    new_button = bot.set_chat_menu_button.await_args_list[-1].kwargs["menu_button"]
    assert isinstance(new_button, MenuButtonWebApp)
    assert new_button.web_app.url == "https://web.example/alt/profile"

    main.menu_button_post_init.assert_not_awaited()


@pytest.mark.asyncio
async def test_post_init_restores_default_when_webapp_url_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Menu button falls back to default after the WebApp URL is cleared."""

    monkeypatch.setenv("WEBAPP_URL", "https://web.example/app")
    main = _reload_main()
    bot = SimpleNamespace(
        set_my_commands=AsyncMock(),
        set_chat_menu_button=AsyncMock(),
    )

    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())

    real_menu_post_init = main.menu_button_post_init
    fallback_mock = AsyncMock(side_effect=real_menu_post_init)
    monkeypatch.setattr(main, "menu_button_post_init", fallback_mock)

    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}

    await main.post_init(app)

    assert bot.set_chat_menu_button.await_count == 1
    first_button = bot.set_chat_menu_button.await_args_list[0].kwargs["menu_button"]
    assert isinstance(first_button, MenuButtonDefault)
    assert fallback_mock.await_count == 0

    monkeypatch.delenv("WEBAPP_URL", raising=False)

    await main.post_init(app)

    assert fallback_mock.await_count == 1
    assert bot.set_chat_menu_button.await_count == 2
    last_button = bot.set_chat_menu_button.await_args_list[-1].kwargs["menu_button"]
    assert isinstance(last_button, MenuButtonDefault)


@pytest.mark.asyncio
async def test_post_init_skips_menu_setup_without_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bot stubs without chat menu support fall back to the default button."""

    monkeypatch.setenv("WEBAPP_URL", "https://web.example/app")
    main = _reload_main()
    bot = SimpleNamespace(set_my_commands=AsyncMock())
    monkeypatch.setattr(memory_service, "get_last_modes", AsyncMock(return_value=[]))
    import services.api.app.diabetes.handlers.assistant_menu as assistant_menu

    monkeypatch.setattr(assistant_menu, "post_init", AsyncMock())
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    app = SimpleNamespace(bot=bot, job_queue=None, user_data=MappingProxyType({}))
    app._user_data = {}

    await main.post_init(app)

    bot.set_my_commands.assert_awaited_once_with(main.commands)
    assert not hasattr(bot, "set_chat_menu_button")
    main.menu_button_post_init.assert_awaited_once()
