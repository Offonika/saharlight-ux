import pytest
from telegram import InlineKeyboardButton

from services.api.app.diabetes.utils.ui import subscription_keyboard


def test_subscription_keyboard_uses_updated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBSCRIPTION_URL", "https://example.com/sub1")
    kb1 = subscription_keyboard(False)
    btn1 = kb1.inline_keyboard[0][0]
    assert isinstance(btn1, InlineKeyboardButton)
    assert btn1.web_app and btn1.web_app.url == "https://example.com/sub1"

    monkeypatch.setenv("SUBSCRIPTION_URL", "https://example.com/sub2")
    kb2 = subscription_keyboard(False)
    btn2 = kb2.inline_keyboard[0][0]
    assert btn2.web_app and btn2.web_app.url == "https://example.com/sub2"

    monkeypatch.delenv("SUBSCRIPTION_URL", raising=False)
