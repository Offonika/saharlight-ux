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

from diabetes.db import SessionLocal, Profile
from diabetes.ui import back_keyboard, menu_keyboard
from .common_handlers import commit_session

SOS_CONTACT, = range(1)


async def sos_contact_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Prompt user to enter emergency contact."""
    await update.message.reply_text(
        "Введите контакт в Telegram (@username) или телефон.",
        reply_markup=back_keyboard,
    )
    return SOS_CONTACT


def _is_valid_contact(text: str) -> bool:
    """Validate telegram username or phone number."""
    username = re.fullmatch(r"@\w{5,32}", text)
    phone = re.fullmatch(r"\+?\d{5,15}", text)
    return bool(username or phone)


async def sos_contact_save(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Save provided contact to profile."""
    contact = update.message.text.strip()
    if not _is_valid_contact(contact):
        await update.message.reply_text(
            "❗ Укажите @username или телефон в международном формате.",
            reply_markup=back_keyboard,
        )
        return SOS_CONTACT

    user_id = update.effective_user.id
    with SessionLocal() as session:
        profile = session.get(Profile, user_id)
        if not profile:
            profile = Profile(telegram_id=user_id)
            session.add(profile)
        profile.sos_contact = contact
        if not commit_session(session):
            await update.message.reply_text(
                "⚠️ Не удалось сохранить контакт.",
                reply_markup=menu_keyboard,
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "✅ Контакт для SOS сохранён.",
        reply_markup=menu_keyboard,
    )
    return ConversationHandler.END


async def sos_contact_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel SOS contact input."""
    await update.message.reply_text("Отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END


sos_contact_conv = ConversationHandler(
    entry_points=[CommandHandler("soscontact", sos_contact_start)],
    states={SOS_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sos_contact_save)]},
    fallbacks=[
        MessageHandler(filters.Regex("^↩️ Назад$"), sos_contact_cancel),
        CommandHandler("cancel", sos_contact_cancel),
    ],
    per_message=False,
)

__all__ = ["sos_contact_conv"]
