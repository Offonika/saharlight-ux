# file: diabetes/ui.py
"""
UI-компоненты бота «Diabet Buddy».
Здесь живут все клавиатуры (Reply и Inline) и их генераторы.
Импортируйте объекты напрямую:

    from services.api.app.diabetes.utils.ui import (
        build_menu_keyboard,
        dose_keyboard,
        confirm_keyboard,
    )
"""

from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)
from services.api.app.config import settings

__all__ = (
    "build_menu_keyboard",
    "dose_keyboard",
    "sugar_keyboard",
    "confirm_keyboard",
    "back_keyboard",
    "build_timezone_webapp_button",
)

# ─────────────── Reply-клавиатуры (отображаются на экране чата) ───────────────


def build_menu_keyboard() -> ReplyKeyboardMarkup:
    """Create the main menu keyboard with optional WebApp buttons.

    A fresh ``ReplyKeyboardMarkup`` is returned on each call so that the
    ``WEBAPP_URL`` setting is read dynamically.
    """

    profile_button = (
        KeyboardButton(
            "📄 Мой профиль", web_app=WebAppInfo(f"{settings.webapp_url}/profile")
        )
        if settings.webapp_url
        else KeyboardButton("📄 Мой профиль")
    )
    reminders_button = (
        KeyboardButton(
            "⏰ Напоминания", web_app=WebAppInfo(f"{settings.webapp_url}/reminders")
        )
        if settings.webapp_url
        else KeyboardButton("⏰ Напоминания")
    )

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📷 Фото еды"), KeyboardButton("🩸 Уровень сахара")],
            [KeyboardButton("💉 Доза инсулина"), KeyboardButton("📊 История")],
            [KeyboardButton("📈 Отчёт"), profile_button],
            [KeyboardButton("🕹 Быстрый ввод"), KeyboardButton("ℹ️ Помощь")],
            [reminders_button, KeyboardButton("🆘 SOS контакт")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие…",
    )

dose_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("ХЕ"), KeyboardButton("Углеводы")],
        [KeyboardButton("↩️ Назад")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Выберите метод расчёта…",
)

sugar_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("↩️ Назад")]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Введите уровень сахара…",
)

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("↩️ Назад")]],
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
            InlineKeyboardButton("✏️ Исправить",  callback_data="edit_entry"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_entry"),
        ],
    ]
    if back_cb:
        rows.append(
            [InlineKeyboardButton("🔙 Назад", callback_data=back_cb)]
        )
    return InlineKeyboardMarkup(rows)


def build_timezone_webapp_button() -> InlineKeyboardButton | None:
    """Create a WebApp button for timezone detection if configured.

    Returns
    -------
    InlineKeyboardButton | None
        Button instance when ``WEBAPP_URL`` is set and valid, otherwise ``None``.
    """

    if not settings.webapp_url:
        return None

    return InlineKeyboardButton(
        "Определить автоматически",
        web_app=WebAppInfo(f"{settings.webapp_url}/timezone"),
    )
