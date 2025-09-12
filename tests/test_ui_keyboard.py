import importlib

import pytest


def _reload_keyboard():
    import services.api.app.ui.keyboard as keyboard

    return importlib.reload(keyboard)


def test_learn_button_text_has_emoji() -> None:
    keyboard = _reload_keyboard()

    assert keyboard.LEARN_BUTTON_TEXT == "🤖 Ассистент_AI"


def test_learn_button_text_without_emoji(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSISTANT_MENU_EMOJI", "false")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    import importlib
    import services.api.app.config as app_config

    importlib.reload(app_config)
    keyboard = _reload_keyboard()

    assert keyboard.LEARN_BUTTON_TEXT == "Ассистент_AI"

    monkeypatch.setenv("ASSISTANT_MENU_EMOJI", "true")
    monkeypatch.delenv("TELEGRAM_TOKEN")
    monkeypatch.delenv("OPENAI_API_KEY")
    importlib.reload(app_config)
    _reload_keyboard()


__all__ = [
    "test_learn_button_text_has_emoji",
    "test_learn_button_text_without_emoji",
]
