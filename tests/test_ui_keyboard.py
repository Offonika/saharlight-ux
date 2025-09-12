import importlib

import pytest

from services.api.app import config


def _reload_keyboard():
    import services.api.app.ui.keyboard as keyboard

    return importlib.reload(keyboard)


def test_learn_button_text_has_emoji() -> None:
    keyboard = _reload_keyboard()

    assert keyboard.LEARN_BUTTON_TEXT == "🤖 Ассистент_AI"


def test_learn_button_text_without_emoji(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSISTANT_MENU_EMOJI", "false")
    config.reload_settings()
    keyboard = _reload_keyboard()

    assert keyboard.LEARN_BUTTON_TEXT == "Ассистент_AI"

    monkeypatch.setenv("ASSISTANT_MENU_EMOJI", "true")
    config.reload_settings()
    _reload_keyboard()


__all__ = [
    "test_learn_button_text_has_emoji",
    "test_learn_button_text_without_emoji",
]

