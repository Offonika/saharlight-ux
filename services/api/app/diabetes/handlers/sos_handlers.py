"""Handlers for managing emergency SOS contact information."""

from __future__ import annotations

import re
from typing import Any, cast

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import (
    Profile,
    SessionLocal,
    User,
    run_db,
)

from services.api.app.diabetes.utils.ui import (
    BACK_BUTTON_TEXT,
    PHOTO_BUTTON_PATTERN,
    back_keyboard,
)
from services.api.app.ui.keyboard import build_main_keyboard
from services.api.app.diabetes.services.repository import CommitError, commit

from . import dose_calc, _cancel_then

(SOS_CONTACT,) = range(1)


async def sos_contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter emergency contact."""
    message = update.message
    chat = getattr(update, "effective_chat", None)
    if message is None:
        if chat is not None:
            await chat.send_message(
                "⚠️ Команда поддерживает только текстовые сообщения.",
                reply_markup=build_main_keyboard(),
            )
        return ConversationHandler.END
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


async def sos_contact_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save provided contact to profile."""
    message = update.message
    chat = getattr(update, "effective_chat", None)
    if message is None:
        if chat is not None:
            await chat.send_message(
                "⚠️ Команда поддерживает только текстовые сообщения.",
                reply_markup=build_main_keyboard(),
            )
        return ConversationHandler.END
    text = message.text
    if text is None:
        await message.reply_text(
            "❗ Укажите @username или числовой ID. Телефоны не поддерживаются.",
            reply_markup=back_keyboard,
        )
        return SOS_CONTACT
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
    user_id = user.id
    user_data = cast(dict[str, Any], context.user_data)

    def _save(
        session: Session,
        user_id: int,
        contact: str,
        thread_id: str | None,
    ) -> bool:
        db_user = session.get(User, user_id)
        if db_user is None:
            if thread_id is None:
                return False
            session.add(User(telegram_id=user_id, thread_id=thread_id))
        profile = session.get(Profile, user_id)
        if profile is None:
            profile = Profile(telegram_id=user_id)
            session.add(profile)
        profile.sos_contact = contact
        try:
            commit(session)
        except CommitError:
            return False
        return True

    thread_id = cast(str | None, user_data.get("thread_id"))
    saved = await run_db(
        _save,
        user_id,
        contact,
        thread_id,
        sessionmaker=SessionLocal,
    )
    if not saved:
        await message.reply_text(
            "⚠️ Не удалось сохранить контакт.",
            reply_markup=build_main_keyboard(),
        )
        return ConversationHandler.END

    await message.reply_text(
        "✅ Контакт для SOS сохранён.",
        reply_markup=build_main_keyboard(),
    )
    return ConversationHandler.END


async def sos_contact_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel SOS contact input."""
    message = update.message
    chat = getattr(update, "effective_chat", None)
    if message is None:
        if chat is not None:
            await chat.send_message("Отменено.", reply_markup=build_main_keyboard())
        return ConversationHandler.END
    await message.reply_text("Отменено.", reply_markup=build_main_keyboard())
    return ConversationHandler.END


sos_contact_conv = ConversationHandler(
    entry_points=[CommandHandler("soscontact", sos_contact_start)],
    states={
        SOS_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sos_contact_save)]
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), sos_contact_cancel),
        CommandHandler("cancel", sos_contact_cancel),
        MessageHandler(
            filters.Regex(PHOTO_BUTTON_PATTERN),
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
