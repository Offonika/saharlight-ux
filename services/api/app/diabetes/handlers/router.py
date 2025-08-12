from __future__ import annotations

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes

from services.api.app.diabetes.services.db import Entry, SessionLocal
from services.api.app.diabetes.utils.ui import menu_keyboard

from .db_helpers import commit_session

logger = logging.getLogger(__name__)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for pending entries and history actions."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data.startswith("rem_"):
        return

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
        sugar = entry_data.get("sugar_before")
        if sugar is not None:
            from .alert_handlers import check_alert
            await check_alert(update, context, sugar)
        await query.edit_message_text("✅ Запись сохранена в дневник!")
        from . import reminder_handlers

        job_queue = getattr(context, "job_queue", None)
        if job_queue:
            reminder_handlers.schedule_after_meal(update.effective_user.id, job_queue)
        return
    elif data == "edit_entry":
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
    elif data == "cancel_entry":
        context.user_data.pop("pending_entry", None)
        await query.edit_message_text("❌ Запись отменена.")
        await query.message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard)
        return
    elif data.startswith("edit:") or data.startswith("del:"):
        action, entry_id = data.split(":", 1)
        try:
            entry_id = int(entry_id)
        except ValueError:
            logger.warning("Invalid entry_id in callback data: %s", entry_id)
            await query.edit_message_text("Некорректный идентификатор записи.")
            return
        with SessionLocal() as session:
            entry = session.get(Entry, entry_id)
            if not entry:
                await query.edit_message_text("Запись не найдена (уже удалена).")
                return
            if entry.telegram_id != update.effective_user.id:
                await query.edit_message_text(
                    "⚠️ Эта запись принадлежит другому пользователю."
                )
                return
            if action == "del":
                session.delete(entry)
                if not commit_session(session):
                    await query.edit_message_text("⚠️ Не удалось удалить запись.")
                    return
                await query.edit_message_text("❌ Запись удалена.")
                return
            if action == "edit":
                context.user_data["edit_entry"] = {
                    "id": entry.id,
                    "chat_id": query.message.chat_id,
                    "message_id": query.message.message_id,
                }
                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "сахар", callback_data=f"edit_field:{entry.id}:sugar"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "xe", callback_data=f"edit_field:{entry.id}:xe"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "dose", callback_data=f"edit_field:{entry.id}:dose"
                            )
                        ],
                    ]
                )
                await query.edit_message_reply_markup(reply_markup=keyboard)
                return
    elif data.startswith("edit_field:"):
        try:
            _, entry_id_str, field = data.split(":")
            entry_id = int(entry_id_str)
        except ValueError:
            logger.warning("Invalid edit_field data: %s", data)
            await query.edit_message_text("Некорректные данные для редактирования.")
            return
        context.user_data["edit_id"] = entry_id
        context.user_data["edit_field"] = field
        context.user_data["edit_query"] = query
        prompt = {
            "sugar": "Введите уровень сахара (ммоль/л).",
            "xe": "Введите количество ХЕ.",
            "dose": "Введите дозу инсулина (ед.).",
        }.get(field, "Введите значение")
        await query.message.reply_text(prompt, reply_markup=ForceReply(selective=True))
        return
    else:
        logger.warning("Unrecognized callback data: %s", data)
        await query.edit_message_text("Команда не распознана")
