import importlib
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from pathlib import Path
from telegram import InlineKeyboardButton, Update
from telegram.ext import CallbackContext

import services.api.app.config as config
import services.api.app.diabetes.utils.ui as ui

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.onboarding_handlers"
)


def test_timezone_button_webapp_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should not build button when PUBLIC_ORIGIN and UI_BASE_URL are unset."""
    monkeypatch.setenv("PUBLIC_ORIGIN", "")
    monkeypatch.setenv("UI_BASE_URL", "")
    config.reload_settings()

    assert ui.build_timezone_webapp_button() is None


def test_timezone_button_webapp_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return a button pointing to the timezone webapp."""
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    config.reload_settings()

    button = ui.build_timezone_webapp_button()
    assert isinstance(button, InlineKeyboardButton)
    assert button.text == "Автоопределить (WebApp)"
    web_app = button.web_app
    assert web_app is not None
    assert web_app.url.endswith("/timezone.html")


def test_timezone_page_loads_sdk_and_sends_timezone() -> None:
    """Timezone webapp should include Telegram SDK and send timezone."""
    html = Path("services/webapp/ui/public/timezone.html").read_text(encoding="utf-8")
    assert "https://telegram.org/js/telegram-web-app.js" in html
    assert "window.Telegram.WebApp.sendData" in html


@pytest.mark.asyncio
async def test_timezone_webapp_saves_tz_and_moves_to_reminders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = SimpleNamespace(web_app_data=SimpleNamespace(data="Asia/Tokyo"))
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message, effective_user=SimpleNamespace(id=1)
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    monkeypatch.setattr(
        handlers.onboarding_state, "load_state", AsyncMock(return_value=None)
    )
    prompt = AsyncMock(return_value=handlers.REMINDERS)
    monkeypatch.setattr(handlers, "_prompt_reminders", prompt)
    state = await handlers.timezone_webapp(update, context)
    assert state == handlers.REMINDERS
    assert context.user_data["timezone"] == "Asia/Tokyo"
    prompt.assert_awaited_once()
