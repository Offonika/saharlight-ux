import pytest
from pathlib import Path
from telegram import InlineKeyboardButton

import services.api.app.config as config
import services.api.app.diabetes.utils.ui as ui


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
    web_app = button.web_app
    assert web_app is not None
    assert web_app.url.endswith("/timezone.html")


def test_timezone_page_loads_sdk_and_sends_timezone() -> None:
    """Timezone webapp should include Telegram SDK and send timezone."""
    html = Path("services/webapp/ui/src/pages/timezone.html").read_text(encoding="utf-8")
    assert "https://telegram.org/js/telegram-web-app.js" in html
    assert "window.Telegram.WebApp.sendData" in html
