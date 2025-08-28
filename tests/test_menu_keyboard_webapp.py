from urllib.parse import urlparse

import pytest

import services.api.app.diabetes.utils.ui as ui


@pytest.mark.parametrize(
    "origin, ui_base",
    [
        ("https://example.com", ""),
        ("https://example.com/", ""),
        ("https://example.com", "/ui"),
        ("https://example.com/", "/ui/"),
    ],
)
def test_menu_keyboard_webapp_urls(
    monkeypatch: pytest.MonkeyPatch, origin: str, ui_base: str
) -> None:
    """Menu buttons should open webapp paths for profile and reminders."""
    monkeypatch.setenv("PUBLIC_ORIGIN", origin)
    monkeypatch.setenv("UI_BASE_URL", ui_base)

    buttons = [btn for row in ui.menu_keyboard().keyboard for btn in row]
    profile_btn = next(b for b in buttons if b.text == ui.PROFILE_BUTTON_TEXT)
    reminders_btn = next(b for b in buttons if b.text == ui.REMINDERS_BUTTON_TEXT)

    assert profile_btn.web_app is not None
    assert urlparse(profile_btn.web_app.url).path.endswith("/profile")
    assert reminders_btn.web_app is not None
    assert urlparse(reminders_btn.web_app.url).path.endswith("/reminders")


def test_menu_keyboard_webapp_reloads_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """``menu_keyboard`` should reflect environment changes at runtime."""
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("UI_BASE_URL", raising=False)
    buttons = [btn for row in ui.menu_keyboard().keyboard for btn in row]
    profile_btn = next(b for b in buttons if b.text == ui.PROFILE_BUTTON_TEXT)
    reminders_btn = next(b for b in buttons if b.text == ui.REMINDERS_BUTTON_TEXT)
    assert profile_btn.web_app is None
    assert reminders_btn.web_app is None

    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "")
    buttons = [btn for row in ui.menu_keyboard().keyboard for btn in row]
    profile_btn = next(b for b in buttons if b.text == ui.PROFILE_BUTTON_TEXT)
    reminders_btn = next(b for b in buttons if b.text == ui.REMINDERS_BUTTON_TEXT)
    assert profile_btn.web_app is not None
    assert reminders_btn.web_app is not None
    assert urlparse(profile_btn.web_app.url).path.endswith("/profile")
    assert urlparse(reminders_btn.web_app.url).path.endswith("/reminders")
