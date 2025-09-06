from types import SimpleNamespace
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from services.api.app.diabetes.handlers.profile.formatters import profile_view_formatter


def test_profile_view_formatter_existing_profile() -> None:
    profile = SimpleNamespace(
        icr=8.0,
        cf=3.0,
        target=6.0,
        low=4.0,
        high=9.0,
        sos_contact="+123",
        sos_alerts_enabled=True,
    )
    text, markup = profile_view_formatter(profile, None)
    assert "📄 Ваш профиль" in text
    assert "• ИКХ: 8.0 г/ед." in text
    assert isinstance(markup, InlineKeyboardMarkup)
    buttons = [b.text for row in markup.inline_keyboard for b in row]
    assert "✏️ Изменить" in buttons
    assert "🔙 Назад" in buttons


def test_profile_view_formatter_no_profile_button() -> None:
    button = InlineKeyboardButton("open", url="https://example.com")
    text, markup = profile_view_formatter(None, [button])
    assert "Ваш профиль пока не настроен" in text
    assert isinstance(markup, InlineKeyboardMarkup)
    assert markup.inline_keyboard[0][0].text == "open"
