from types import SimpleNamespace

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from services.api.app.diabetes.handlers.profile.formatter import (
    profile_view_formatter,
)


def test_profile_view_formatter_no_profile() -> None:
    text, keyboard = profile_view_formatter(None)
    assert "пока не настроен" in text
    assert keyboard is None


def test_profile_view_formatter_with_profile() -> None:
    profile = SimpleNamespace(
        icr=8,
        cf=3,
        target=6,
        low=4,
        high=9,
        quiet_start={"hour": 8, "minute": 30},
        quiet_end={"hour": 22, "minute": 15},
    )
    button = InlineKeyboardButton("open", callback_data="cb")
    text, keyboard = profile_view_formatter(profile, [button])
    assert "08:30-22:15" in text
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert any(btn.text == "open" for row in keyboard.inline_keyboard for btn in row)
