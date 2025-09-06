from telegram import ReplyKeyboardMarkup, KeyboardButton

LEARN_BUTTON_TEXT = "🎓 Обучение"


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(LEARN_BUTTON_TEXT)]],
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие…",
    )


__all__ = ["LEARN_BUTTON_TEXT", "build_main_keyboard"]
