# file: diabetes/ui.py
"""
UI-компоненты бота «Diabet Buddy».
Здесь живут все клавиатуры (Reply и Inline) и их генераторы.
Импортируйте объекты напрямую:

    from services.api.app.diabetes.utils.ui import menu_keyboard, dose_keyboard, confirm_keyboard
"""

from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)
from services.api.app import config

PROFILE_BUTTON_TEXT = "📄 Мой профиль"
REMINDERS_BUTTON_TEXT = "⏰ Напоминания"
PHOTO_BUTTON_TEXT = "📷 Фото еды"
SUGAR_BUTTON_TEXT = "🩸 Уровень сахара"
DOSE_BUTTON_TEXT = "💉 Доза инсулина"
HISTORY_BUTTON_TEXT = "📊 История"
REPORT_BUTTON_TEXT = "📈 Отчёт"
QUICK_INPUT_BUTTON_TEXT = "🕹 Быстрый ввод"
HELP_BUTTON_TEXT = "ℹ️ Помощь"
SOS_BUTTON_TEXT = "🆘 SOS контакт"
BACK_BUTTON_TEXT = "↩️ Назад"
XE_BUTTON_TEXT = "ХЕ"
CARBS_BUTTON_TEXT = "Углеводы"

__all__ = (
    "menu_keyboard",
    "dose_keyboard",
    "sugar_keyboard",
    "confirm_keyboard",
    "back_keyboard",
    "build_timezone_webapp_button",
    "PROFILE_BUTTON_TEXT",
    "REMINDERS_BUTTON_TEXT",
    "PHOTO_BUTTON_TEXT",
    "SUGAR_BUTTON_TEXT",
    "DOSE_BUTTON_TEXT",
    "HISTORY_BUTTON_TEXT",
    "REPORT_BUTTON_TEXT",
    "QUICK_INPUT_BUTTON_TEXT",
    "HELP_BUTTON_TEXT",
    "SOS_BUTTON_TEXT",
    "BACK_BUTTON_TEXT",
    "XE_BUTTON_TEXT",
    "CARBS_BUTTON_TEXT",
)


def _webapp_url() -> str | None:
    """Return ``settings.webapp_url`` without a trailing slash."""

    url = config.settings.webapp_url
    return url.rstrip("/") if url else None


def menu_keyboard() -> ReplyKeyboardMarkup:
    """Build the main menu keyboard.

    ``settings.webapp_url`` is read at call time to determine whether WebApp
    buttons should be used for profile and reminders.
    """

    webapp_url = _webapp_url()
    profile_button = (
        KeyboardButton(
            PROFILE_BUTTON_TEXT, web_app=WebAppInfo(f"{webapp_url}/profile")
        )
        if webapp_url
        else KeyboardButton(PROFILE_BUTTON_TEXT)
    )
    reminders_button = (
        KeyboardButton(
            REMINDERS_BUTTON_TEXT, web_app=WebAppInfo(f"{webapp_url}/reminders")
        )
        if webapp_url
        else KeyboardButton(REMINDERS_BUTTON_TEXT)
    )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(PHOTO_BUTTON_TEXT), KeyboardButton(SUGAR_BUTTON_TEXT)],
            [KeyboardButton(DOSE_BUTTON_TEXT), KeyboardButton(HISTORY_BUTTON_TEXT)],
            [KeyboardButton(REPORT_BUTTON_TEXT), profile_button],
            [KeyboardButton(QUICK_INPUT_BUTTON_TEXT), KeyboardButton(HELP_BUTTON_TEXT)],
            [reminders_button, KeyboardButton(SOS_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие…",
    )

dose_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(XE_BUTTON_TEXT), KeyboardButton(CARBS_BUTTON_TEXT)],
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

    webapp_url = _webapp_url()
    if not webapp_url:
        return None

    return InlineKeyboardButton(
        "Определить автоматически",
        web_app=WebAppInfo(f"{webapp_url}/timezone"),
    )
