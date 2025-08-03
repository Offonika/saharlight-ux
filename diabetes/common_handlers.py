"""Common utility handlers and helpers.

This module contains utilities shared across different handler modules,
including database transaction helpers and callback query routing.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.exc import SQLAlchemyError

from diabetes.db import SessionLocal, Entry
from diabetes.ui import menu_keyboard

logger = logging.getLogger(__name__)


def commit_session(session) -> bool:
    """Commit an SQLAlchemy session.

    Parameters
    ----------
    session: Session
        Active SQLAlchemy session.

    Returns
    -------
    bool
        ``True`` if the commit succeeded. If an error occurs the session is
        rolled back, the error is logged and ``False`` is returned.
    """
    try:
        session.commit()
        return True
    except SQLAlchemyError as exc:  # pragma: no cover - logging only
        session.rollback()
        logger.error("DB commit failed: %s", exc)
        return False


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for pending entries and history actions."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "confirm_entry":
        entry_data = context.user_data.pop("pending_entry", None)
        if not entry_data:
            await query.edit_message_text("❗ Нет данных для сохранения.")
            return
        with SessionLocal() as session:
            entry = Entry(**entry_data)
            session.add(entry)
            if not commit_session(session):
                await query.edit_message_text("⚠️ Не удалось сохранить запись.")
                return
        await query.edit_message_text("✅ Запись сохранена в дневник!")
        return

    if data == "edit_entry":
        entry_data = context.user_data.get("pending_entry")
        if not entry_data:
            await query.edit_message_text("❗ Нет данных для редактирования.")
            return
        context.user_data["edit_id"] = None
        await query.edit_message_text(
            "Отправьте новое сообщение в формате:\n"
            "`сахар=<ммоль/л>  xe=<ХЕ>  carbs=<г>  dose=<ед>`\n"
            "Можно указывать не все поля (что прописано — то и поменяется).",
            parse_mode="Markdown",
        )
        return

    if data == "cancel_entry":
        context.user_data.pop("pending_entry", None)
        await query.edit_message_text("❌ Запись отменена.")
        await query.message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard)
        return

    if ":" in data:
        action, entry_id = data.split(":", 1)
        with SessionLocal() as session:
            entry = session.get(Entry, int(entry_id))
            if not entry:
                await query.edit_message_text("Запись не найдена (уже удалена).")
                return
            if action == "del":
                session.delete(entry)
                if not commit_session(session):
                    await query.edit_message_text("⚠️ Не удалось удалить запись.")
                    return
                await query.edit_message_text("❌ Запись удалена.")
                return
            if action == "edit":
                context.user_data["edit_id"] = entry.id
                text = (
                    "Отправьте новое сообщение в формате:\n"
                    "`сахар=<ммоль/л>  xe=<ХЕ>  carbs=<г>  dose=<ед>`\n"
                    "Можно указывать не все поля (что прописано — то и поменяется).",
                )
                await query.edit_message_text("\n".join(text), parse_mode="Markdown")
                return


def register_handlers(app) -> None:
    """Register bot handlers (placeholder)."""
    # Actual handler registration lives elsewhere.
    return


__all__ = [
    "commit_session",
    "callback_router",
    "menu_keyboard",
]
