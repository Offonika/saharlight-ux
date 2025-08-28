from urllib.parse import urlparse

import pytest

import services.api.app.diabetes.utils.ui as ui


def test_timezone_button_webapp_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Button should be returned when PUBLIC_ORIGIN is configured."""

    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "/ui")

    button = ui.build_timezone_webapp_button()
    assert button is not None
    web_app = button.web_app
    assert web_app is not None
    assert urlparse(web_app.url).path == "/ui/timezone"


def test_timezone_button_webapp_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """No button is built when PUBLIC_ORIGIN is missing."""

    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)

    button = ui.build_timezone_webapp_button()
    assert button is None
