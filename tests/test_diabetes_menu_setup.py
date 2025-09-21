"""Tests for configuring chat menu WebApp shortcuts."""

from __future__ import annotations

import pytest
from telegram import MenuButtonWebApp
from telegram.ext import Application, ExtBot

import services.api.app.config as config


@pytest.mark.asyncio
async def test_setup_chat_menu_configures_webapp_buttons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chat menu exposes four WebApp shortcuts derived from ``WEBAPP_URL``."""

    monkeypatch.setenv("WEBAPP_URL", "https://web.example/app")
    config.reload_settings()

    from services.api.app.diabetes.utils.menu_setup import setup_chat_menu

    stored_menu: list[MenuButtonWebApp] | None = None

    async def fake_set_chat_menu_button(
        self: ExtBot, *args: object, **kwargs: object
    ) -> bool:
        nonlocal stored_menu
        stored_menu = kwargs["menu_button"]
        return True

    async def fake_get_chat_menu_button(
        self: ExtBot, *args: object, **kwargs: object
    ) -> list[MenuButtonWebApp] | None:
        return stored_menu

    monkeypatch.setattr(ExtBot, "set_chat_menu_button", fake_set_chat_menu_button)
    monkeypatch.setattr(ExtBot, "get_chat_menu_button", fake_get_chat_menu_button)

    app = Application.builder().token("TOKEN").build()
    await setup_chat_menu(app.bot)

    menu = await app.bot.get_chat_menu_button()
    assert menu is not None
    assert isinstance(menu, list)
    assert len(menu) == 4
    assert all(isinstance(button, MenuButtonWebApp) for button in menu)

    expected_labels = ["Profile", "Reminders", "History", "Analytics"]
    expected_paths = ["profile", "reminders", "history", "analytics"]

    for button, label, path in zip(menu, expected_labels, expected_paths, strict=True):
        assert button.text == label
        assert button.web_app.url == f"https://web.example/app/{path}"
