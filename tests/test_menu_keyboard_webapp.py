import pytest

import importlib
from urllib.parse import urlparse


def test_menu_keyboard_webapp_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Menu buttons should open webapp paths for profile and reminders."""
    monkeypatch.setenv("WEBAPP_URL", "https://example.com")

    import services.api.app.config as config
    import services.api.app.diabetes.utils.ui as ui

    importlib.reload(config)
    importlib.reload(ui)

    buttons = [btn for row in ui.menu_keyboard.keyboard for btn in row]
    profile_btn = next(b for b in buttons if b.text == "📄 Мой профиль")
    reminders_btn = next(b for b in buttons if b.text == "⏰ Напоминания")

    assert profile_btn.web_app is not None
    assert urlparse(profile_btn.web_app.url).path == "/profile"
    assert reminders_btn.web_app is not None
    assert urlparse(reminders_btn.web_app.url).path == "/reminders"

    monkeypatch.delenv("WEBAPP_URL", raising=False)
    importlib.reload(config)
    importlib.reload(ui)