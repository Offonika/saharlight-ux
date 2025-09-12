from telegram import ReplyKeyboardMarkup, KeyboardButton

from services.api.app.diabetes.utils.ui import menu_keyboard
from services.api.app.config import get_settings

_settings = get_settings()
LEARN_BUTTON_TEXT = (
    "🤖 Ассистент_AI" if _settings.assistant_menu_emoji else "Ассистент_AI"
)


def build_main_keyboard() -> ReplyKeyboardMarkup:
    """Build main menu keyboard with extra assistant button."""
    menu = menu_keyboard()
    layout = [row[:] for row in menu.keyboard]
    layout.append((KeyboardButton(LEARN_BUTTON_TEXT),))
    return ReplyKeyboardMarkup(
        keyboard=layout,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder=menu.input_field_placeholder,
    )


__all__ = [
    "LEARN_BUTTON_TEXT",
    "build_main_keyboard",
]
