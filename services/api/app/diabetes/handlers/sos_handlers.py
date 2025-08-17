"""Handlers for managing emergency SOS contact information."""

from __future__ import annotations

import re

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services.api.app.diabetes.services.db import SessionLocal, Profile
from services.api.app.diabetes.utils.ui import back_keyboard, menu_keyboard
from services.api.app.diabetes.services.repository import commit
from . import dose_calc, _cancel_then

SOS_CONTACT, = range(1)


async def sos_contact_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Prompt user to enter emergency contact."""
    message = update.message
    if message is None:
        return ConversationHandler.END
    assert message is not None
    await message.reply_text(
        "Введите контакт в Telegram (@username). Телефоны не поддерживаются.",
        reply_markup=back_keyboard,
    )
    return SOS_CONTACT


def _is_valid_contact(text: str) -> bool:
    """Validate telegram username or numeric chat ID."""
    username = re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{4,31}", text)
    chat_id = re.fullmatch(r"\d+", text)
    return bool(username or chat_id)


async def sos_contact_save(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Save provided contact to profile."""
    message = update.message
    if message is None:
        return ConversationHandler.END
    text = message.text
    if text is None:
        return ConversationHandler.END
    assert message is not None
    assert text is not None
    contact = text.strip()
    if not _is_valid_contact(contact):
        await message.reply_text(
            "❗ Укажите @username или числовой ID. Телефоны не поддерживаются.",
            reply_markup=back_keyboard,
        )
        return SOS_CONTACT
    user = update.effective_user
    if user is None:
        return ConversationHandler.END
    assert user is not None
    user_id = user.id
    with SessionLocal() as session:
        profile = session.get(Profile, user_id)
        if not profile:
            profile = Profile(telegram_id=user_id)
            session.add(profile)
        profile.sos_contact = contact
        if not commit(session):
            await message.reply_text(
                "⚠️ Не удалось сохранить контакт.",
                reply_markup=menu_keyboard,
            )
            return ConversationHandler.END

    await message.reply_text(
        "✅ Контакт для SOS сохранён.",
        reply_markup=menu_keyboard,
    )
    return ConversationHandler.END


async def sos_contact_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel SOS contact input."""
    message = update.message
    if message is None:
        return ConversationHandler.END
    assert message is not None
    await message.reply_text("Отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END


sos_contact_conv = ConversationHandler(
    entry_points=[CommandHandler("soscontact", sos_contact_start)],
    states={SOS_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sos_contact_save)]},
    fallbacks=[
        MessageHandler(filters.Regex("^↩️ Назад$"), sos_contact_cancel),
        CommandHandler("cancel", sos_contact_cancel),
        MessageHandler(
            filters.Regex("^📷 Фото еды$"),
            _cancel_then(dose_calc.photo_prompt),
        ),
    ],
    per_message=False,
)

__all__ = [
    "SOS_CONTACT",
    "sos_contact_start",
    "sos_contact_save",
    "sos_contact_cancel",
    "sos_contact_conv",
    "ConversationHandler",
]
