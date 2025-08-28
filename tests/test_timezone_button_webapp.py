from urllib.parse import urlparse

import pytest

import services.api.app.diabetes.utils.ui as ui


def test_timezone_button_webapp_disabled_without_public_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should not build button when PUBLIC_ORIGIN is missing."""
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("UI_BASE_URL", raising=False)

    assert ui.build_timezone_webapp_button() is None


def test_timezone_button_webapp_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timezone button should open webapp path for timezone detection."""
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    assert ui.build_timezone_webapp_button() is None

    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "/ui")

    button = ui.build_timezone_webapp_button()
    assert button is not None
    web_app = button.web_app
    assert web_app is not None
    assert urlparse(web_app.url).path == "/ui/timezone"
