"""Tests for configuring chat menu buttons."""

from __future__ import annotations

import pytest
from telegram import MenuButton, MenuButtonWebApp
from telegram.ext import Application, ExtBot

import services.api.app.config as config


@pytest.mark.asyncio
async def test_setup_chat_menu_configures_webapp_buttons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chat menu installs the configured WebApp button when ``WEBAPP_URL`` set."""

    monkeypatch.setenv("WEBAPP_URL", "https://web.example/app")
    config.reload_settings()

    from services.api.app.diabetes.utils.menu_setup import setup_chat_menu

    stored_menu: MenuButton | None = None

    async def fake_set_chat_menu_button(
        self: ExtBot, *args: object, **kwargs: object
    ) -> bool:
        nonlocal stored_menu
        stored_menu = kwargs["menu_button"]
        return True

    async def fake_get_chat_menu_button(
        self: ExtBot, *args: object, **kwargs: object
    ) -> MenuButton | None:
        return stored_menu

    monkeypatch.setattr(ExtBot, "set_chat_menu_button", fake_set_chat_menu_button)
    monkeypatch.setattr(ExtBot, "get_chat_menu_button", fake_get_chat_menu_button)

    app = Application.builder().token("TOKEN").build()
    await setup_chat_menu(app.bot)

    menu = await app.bot.get_chat_menu_button()
    assert stored_menu is not None
    assert isinstance(stored_menu, MenuButton)
    assert isinstance(stored_menu, MenuButtonWebApp)
    assert stored_menu.text == "Profile"
    assert stored_menu.web_app.url == "https://web.example/app/profile"
    assert menu is not None
    assert isinstance(menu, MenuButtonWebApp)
    assert menu is stored_menu
