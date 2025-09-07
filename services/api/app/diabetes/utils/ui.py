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
SUBSCRIPTION_BUTTON_TEXT = "💳 Подписка"
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
    "SUBSCRIPTION_BUTTON_TEXT",
    "BACK_BUTTON_TEXT",
    "XE_BUTTON_TEXT",
    "CARBS_BUTTON_TEXT",
    "subscription_keyboard",
)


def menu_keyboard() -> ReplyKeyboardMarkup:
    """Build the main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(PHOTO_BUTTON_TEXT), KeyboardButton(SUGAR_BUTTON_TEXT)],
            [KeyboardButton(DOSE_BUTTON_TEXT), KeyboardButton(REPORT_BUTTON_TEXT)],
            [KeyboardButton(QUICK_INPUT_BUTTON_TEXT), KeyboardButton(HELP_BUTTON_TEXT)],
            [KeyboardButton(SOS_BUTTON_TEXT)],
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


def subscription_keyboard(trial_available: bool) -> InlineKeyboardMarkup:
    """Build inline keyboard for subscription actions."""
    from services.api.app import config

    # Settings values may change during tests or runtime when environment
    # variables are monkeypatched. Reloading here ensures we always read the
    # latest ``SUBSCRIPTION_URL`` or ``PUBLIC_ORIGIN`` values.
    config.reload_settings()
    buttons: list[InlineKeyboardButton] = []
    if trial_available:
        buttons.append(InlineKeyboardButton("🎁 Trial", callback_data="trial"))
    settings = config.get_settings()
    url = settings.subscription_url
    if not url:
        try:
            url = config.build_ui_url("/subscription")
        except RuntimeError:
            url = None
    if url:
        buttons.append(
            InlineKeyboardButton(
                "💳 Оформить PRO",
                web_app=WebAppInfo(url),
            )
        )
    return InlineKeyboardMarkup([buttons] if buttons else [])


def build_timezone_webapp_button() -> InlineKeyboardButton | None:
    """Create a WebApp button for timezone detection if configured.

    Returns
    -------
    InlineKeyboardButton | None
        Button instance when ``PUBLIC_ORIGIN`` is set and valid, otherwise ``None``.
    """

    from services.api.app import config

    config.reload_settings()
    settings = config.get_settings()
    if not settings.public_origin:
        return None

    return InlineKeyboardButton(
        "Автоопределить (WebApp)",
        web_app=WebAppInfo(config.build_ui_url("/timezone.html")),
    )
