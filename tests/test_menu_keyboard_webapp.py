import pytest

import services.api.app.config as config
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
def test_menu_keyboard_contains_expected_buttons(
    monkeypatch: pytest.MonkeyPatch, origin: str, ui_base: str
) -> None:
    """Menu should provide a consistent set of buttons without WebApps."""
    monkeypatch.setenv("PUBLIC_ORIGIN", origin)
    monkeypatch.setenv("UI_BASE_URL", ui_base)
    config.reload_settings()

    buttons = [btn for row in ui.menu_keyboard().keyboard for btn in row]
    texts = {btn.text for btn in buttons}
    expected = {
        ui.PHOTO_BUTTON_TEXT,
        ui.SUGAR_BUTTON_TEXT,
        ui.DOSE_BUTTON_TEXT,
        ui.REPORT_BUTTON_TEXT,
        ui.QUICK_INPUT_BUTTON_TEXT,
        ui.HELP_BUTTON_TEXT,
        ui.SOS_BUTTON_TEXT,
    }
    assert texts == expected
    assert all(btn.web_app is None for btn in buttons)


def test_menu_keyboard_webapp_reloads_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """``menu_keyboard`` should remain without WebApps after config changes."""
    monkeypatch.setenv("PUBLIC_ORIGIN", "")
    monkeypatch.setenv("UI_BASE_URL", "")
    config.reload_settings()
    buttons = [btn for row in ui.menu_keyboard().keyboard for btn in row]
    assert all(btn.web_app is None for btn in buttons)

    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "")
    config.reload_settings()
    buttons = [btn for row in ui.menu_keyboard().keyboard for btn in row]
    assert all(btn.web_app is None for btn in buttons)
