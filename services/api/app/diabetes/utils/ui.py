# file: diabetes/ui.py
"""
UI-компоненты бота «Diabet Buddy».
Здесь живут все клавиатуры (Reply и Inline) и их генераторы.
Импортируйте объекты напрямую:

    from services.api.app.diabetes.utils.ui import menu_keyboard, dose_keyboard, confirm_keyboard
"""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from services.api.app import config

PHOTO_BUTTON_TEXT = "📷 Фото еды"
SUGAR_BUTTON_TEXT = "🩸 Уровень сахара"
DOSE_BUTTON_TEXT = "💉 Доза инсулина"
HISTORY_BUTTON_TEXT = "📊 История"
REPORT_BUTTON_TEXT = "📈 Отчёт"
PROFILE_BUTTON_TEXT = "📄 Мой профиль"
QUICK_INPUT_BUTTON_TEXT = "🕹 Быстрый ввод"
HELP_BUTTON_TEXT = "ℹ️ Помощь"
REMINDERS_BUTTON_TEXT = "⏰ Напоминания"
SOS_CONTACT_BUTTON_TEXT = "🆘 SOS контакт"
BACK_BUTTON_TEXT = "↩️ Назад"

__all__ = (
    "PHOTO_BUTTON_TEXT",
    "SUGAR_BUTTON_TEXT",
    "DOSE_BUTTON_TEXT",
    "HISTORY_BUTTON_TEXT",
    "REPORT_BUTTON_TEXT",
    "PROFILE_BUTTON_TEXT",
    "QUICK_INPUT_BUTTON_TEXT",
    "HELP_BUTTON_TEXT",
    "REMINDERS_BUTTON_TEXT",
    "SOS_CONTACT_BUTTON_TEXT",
    "BACK_BUTTON_TEXT",
    "menu_keyboard",
    "dose_keyboard",
    "sugar_keyboard",
    "confirm_keyboard",
    "back_keyboard",
    "build_timezone_webapp_button",
)

# ─────────────── Reply-клавиатуры (отображаются на экране чата) ───────────────
_WEBAPP_URL = config.settings.webapp_url.rstrip("/") if config.settings.webapp_url else None

# Create WebApp buttons when WebApp is configured, fall back to text buttons otherwise
profile_button = (
    KeyboardButton(PROFILE_BUTTON_TEXT, web_app=WebAppInfo(f"{_WEBAPP_URL}/profile"))
    if _WEBAPP_URL
    else KeyboardButton(PROFILE_BUTTON_TEXT)
)
reminders_button = (
    KeyboardButton(REMINDERS_BUTTON_TEXT, web_app=WebAppInfo(f"{_WEBAPP_URL}/reminders"))
    if _WEBAPP_URL
    else KeyboardButton(REMINDERS_BUTTON_TEXT)
)

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(PHOTO_BUTTON_TEXT), KeyboardButton(SUGAR_BUTTON_TEXT)],
        [KeyboardButton(DOSE_BUTTON_TEXT), KeyboardButton(HISTORY_BUTTON_TEXT)],
        [KeyboardButton(REPORT_BUTTON_TEXT), profile_button],
        [KeyboardButton(QUICK_INPUT_BUTTON_TEXT), KeyboardButton(HELP_BUTTON_TEXT)],
        [reminders_button, KeyboardButton(SOS_CONTACT_BUTTON_TEXT)],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
    input_field_placeholder="Выберите действие…",
)

dose_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("ХЕ"), KeyboardButton("Углеводы")],
        [KeyboardButton(BACK_BUTTON_TEXT)],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Выберите метод расчёта…",
)

sugar_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(BACK_BUTTON_TEXT)]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Введите уровень сахара…",
)

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(BACK_BUTTON_TEXT)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# ─────────────── Inline-клавиатуры (обрабатываются callback-ами) ───────────────


def confirm_keyboard(back_cb: str | None = None) -> InlineKeyboardMarkup:
    """
    Стандартная клавиатура подтверждения:
        ✅ Подтвердить | ✏️ Исправить | ❌ Отмена | 🔙 Назад (опц.)

    Parameters
    ----------
    back_cb : str | None
        callback_data, которое отправит кнопка «Назад».
        Если None, кнопка не добавляется.
    """
    rows = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_entry"),
            InlineKeyboardButton("✏️ Исправить", callback_data="edit_entry"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_entry"),
        ],
    ]
    if back_cb:
        rows.append([InlineKeyboardButton("🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)


def build_timezone_webapp_button() -> InlineKeyboardButton | None:
    """Create a WebApp button for timezone detection if configured.

    Returns
    -------
    InlineKeyboardButton | None
        Button instance when ``WEBAPP_URL`` is set and valid, otherwise ``None``.
    """

    if not _WEBAPP_URL:
        return None

    return InlineKeyboardButton(
        "Определить автоматически",
        web_app=WebAppInfo(f"{_WEBAPP_URL}/timezone"),
    )
