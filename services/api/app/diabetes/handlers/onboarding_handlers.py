"""Simplified onboarding conversation.

Implements three steps with navigation and progress hints:

1. Profile selection via inline buttons.
2. Timezone input with optional WebApp auto-detect button.
3. Reminder presets with ability to finish.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services.api.app.diabetes.services.db import SessionLocal  # noqa: F401
from services.api.app.diabetes.services.repository import commit  # noqa: F401
from services.api.app.diabetes.utils.ui import (
    PHOTO_BUTTON_TEXT,
    build_timezone_webapp_button,
    menu_keyboard,
)

logger = logging.getLogger(__name__)

# Conversation states
PROFILE, TIMEZONE, REMINDERS = range(3)
ONB_PROFILE_ICR = PROFILE

# Callback identifiers
CB_PROFILE_PREFIX = "onb_prof_"
CB_REMINDER_PREFIX = "onb_rem_"
CB_BACK = "onb_back"
CB_SKIP = "onb_skip"
CB_CANCEL = "onb_cancel"
CB_DONE = "onb_done"


def _progress(step: int) -> str:
    return f"Шаг {step}/3"


def _nav_buttons(*, back: bool = False, skip: bool = True) -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    if back:
        buttons.append(InlineKeyboardButton("Назад", callback_data=CB_BACK))
    if skip:
        buttons.append(InlineKeyboardButton("Пропустить", callback_data=CB_SKIP))
    buttons.append(InlineKeyboardButton("Отмена", callback_data=CB_CANCEL))
    return buttons


def _profile_keyboard() -> InlineKeyboardMarkup:
    options = [
        ("СД2 без инсулина", "t2_no"),
        ("СД2 на инсулине", "t2_ins"),
        ("СД1", "t1"),
        ("ГСД", "gdm"),
        ("Родитель", "parent"),
    ]
    rows = [[InlineKeyboardButton(text, callback_data=f"{CB_PROFILE_PREFIX}{code}")] for text, code in options]
    rows.append(_nav_buttons())
    return InlineKeyboardMarkup(rows)


def _timezone_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    auto_btn = build_timezone_webapp_button()
    if auto_btn:
        rows.append([auto_btn])
    rows.append(_nav_buttons(back=True))
    return InlineKeyboardMarkup(rows)


def _reminders_keyboard() -> InlineKeyboardMarkup:
    presets = [
        ("Сахар 08:00", "sugar_08"),
        ("Длинный инсулин 22:00", "long_22"),
        ("Таблетки 09:00", "pills_09"),
    ]
    rows = [[InlineKeyboardButton(text, callback_data=f"{CB_REMINDER_PREFIX}{code}")] for text, code in presets]
    rows.append([InlineKeyboardButton("Готово", callback_data=CB_DONE)])
    rows.append(_nav_buttons(back=True))
    return InlineKeyboardMarkup(rows)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for ``/start`` command."""

    message = update.message
    if message is None:
        return ConversationHandler.END
    await message.reply_text(
        f"{_progress(1)}. Выберите профиль:",
        reply_markup=_profile_keyboard(),
    )
    return PROFILE


async def profile_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle profile selection and navigation from step 1."""

    query = update.callback_query
    if query is None or query.data is None or query.message is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    await query.answer()
    data = query.data
    user_data = cast(dict[str, Any], context.user_data)
    if data == CB_SKIP:
        return await _prompt_timezone(message)
    if data == CB_CANCEL:
        await message.reply_text("Отменено.")
        return ConversationHandler.END
    if data.startswith(CB_PROFILE_PREFIX):
        user_data["profile"] = data[len(CB_PROFILE_PREFIX) :]
        return await _prompt_timezone(message)
    return ConversationHandler.END


async def _prompt_timezone(message: Message) -> int:
    await message.reply_text(
        f"{_progress(2)}. Введите часовой пояс (например, Europe/Moscow).",
        reply_markup=_timezone_keyboard(),
    )
    return TIMEZONE


async def timezone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone text input."""

    message = update.message
    if message is None or message.text is None:
        return ConversationHandler.END
    user_data = cast(dict[str, Any], context.user_data)
    user_data["timezone"] = message.text.strip() or "Europe/Moscow"
    return await _prompt_reminders(message)


async def timezone_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle navigation callbacks in timezone step."""

    query = update.callback_query
    if query is None or query.data is None or query.message is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    await query.answer()
    data = query.data
    if data == CB_BACK:
        return await _prompt_profile(message)
    if data == CB_SKIP:
        return await _prompt_reminders(message)
    if data == CB_CANCEL:
        await message.reply_text("Отменено.")
        return ConversationHandler.END
    return TIMEZONE


async def _prompt_profile(message: Message) -> int:
    await message.reply_text(
        f"{_progress(1)}. Выберите профиль:",
        reply_markup=_profile_keyboard(),
    )
    return PROFILE


async def _prompt_reminders(message: Message) -> int:
    await message.reply_text(
        f"{_progress(3)}. Выберите напоминания:",
        reply_markup=_reminders_keyboard(),
    )
    return REMINDERS


async def reminders_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reminder preset selection and navigation."""

    query = update.callback_query
    if query is None or query.data is None or query.message is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    await query.answer()
    data = query.data
    if data == CB_BACK:
        return await _prompt_timezone(message)
    if data in {CB_SKIP, CB_DONE}:
        return await _finish(message)
    if data == CB_CANCEL:
        await message.reply_text("Отменено.")
        return ConversationHandler.END
    if data.startswith(CB_REMINDER_PREFIX):
        user_data = cast(dict[str, Any], context.user_data)
        reminders = cast(set[str], user_data.setdefault("reminders", set()))
        code = data[len(CB_REMINDER_PREFIX) :]
        if code in reminders:
            reminders.remove(code)
        else:
            reminders.add(code)
        return REMINDERS
    return REMINDERS


async def onboarding_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip onboarding and show final message."""

    query = update.callback_query
    if query is None or query.message is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    await query.answer()
    await message.reply_poll("Пропущено", ["OK"])
    await message.reply_text("Пропущено", reply_markup=menu_keyboard())
    return ConversationHandler.END


async def onboarding_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish onboarding when reminders step is skipped."""

    query = update.callback_query
    if query is None or query.message is None:
        return ConversationHandler.END
    await query.answer()
    message = cast(Message, query.message)
    return await _finish(message)


async def _finish(message: Message) -> int:
    await message.reply_text("🎉 Готово! Настройка завершена.", reply_markup=menu_keyboard())
    return ConversationHandler.END


async def onboarding_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stub for backward compatibility."""

    return None


async def _photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle accidental photo messages during onboarding."""

    message = update.message
    if message is not None:
        await message.reply_text("Отменено.")
        await message.reply_text("Загрузите фото позже через соответствующую команду.")
    user_data = cast(dict[str, Any], context.user_data)
    user_data.clear()
    return ConversationHandler.END


onboarding_conv = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        PROFILE: [CallbackQueryHandler(profile_chosen)],
        TIMEZONE: [
            CallbackQueryHandler(
                timezone_nav,
                pattern=f"^({CB_BACK}|{CB_SKIP}|{CB_CANCEL})$",
            ),
            MessageHandler(filters.TEXT & (~filters.COMMAND), timezone_text),
        ],
        REMINDERS: [CallbackQueryHandler(reminders_chosen)],
    },
    fallbacks=[MessageHandler(filters.Regex(f"^{PHOTO_BUTTON_TEXT}$"), _photo_fallback)],
)

__all__ = [
    "PROFILE",
    "TIMEZONE",
    "REMINDERS",
    "ONB_PROFILE_ICR",
    "start_command",
    "profile_chosen",
    "timezone_text",
    "timezone_nav",
    "reminders_chosen",
    "onboarding_skip",
    "onboarding_reminders",
    "onboarding_poll_answer",
    "onboarding_conv",
]
