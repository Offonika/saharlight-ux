from __future__ import annotations

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes

from services.api.app.diabetes.services.db import Entry, SessionLocal
from services.api.app.diabetes.utils.ui import menu_keyboard

from services.api.app.diabetes.services.repository import commit

logger = logging.getLogger(__name__)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for pending entries and history actions."""
    query = update.callback_query
    if query is None:
        return
    assert query is not None
    await query.answer()
    data = query.data or ""

    if data.startswith("rem_"):
        return

    if data == "confirm_entry":
        user_data = context.user_data
        entry_data = user_data.pop("pending_entry", None)
        if not entry_data:
            await query.edit_message_text("❗ Нет данных для сохранения.")
            return
        with SessionLocal() as session:
            entry = Entry(**entry_data)
            session.add(entry)
            if not commit(session):
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
            user = update.effective_user
            if user is None:
                return
            assert user is not None
            reminder_handlers.schedule_after_meal(user.id, job_queue)
        return
    elif data == "edit_entry":
        user_data = context.user_data
        entry_data = user_data.get("pending_entry")
        if not entry_data:
            await query.edit_message_text("❗ Нет данных для редактирования.")
            return
        user_data["edit_id"] = None
        await query.edit_message_text(
            "Отправьте новое сообщение в формате:\n"
            "`сахар=<ммоль/л>  xe=<ХЕ>  carbs=<г>  dose=<ед>`\n"
            "Можно указывать не все поля (что прописано — то и поменяется).",
            parse_mode="Markdown",
        )
        return
    elif data == "cancel_entry":
        user_data = context.user_data
        user_data.pop("pending_entry", None)
        await query.edit_message_text("❌ Запись отменена.")
        message = query.message
        if message is None:
            return
        assert message is not None
        await message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard)
        return
    elif data.startswith("edit:") or data.startswith("del:"):
        action, entry_id_str = data.split(":", 1)
        try:
            entry_id = int(entry_id_str)
        except ValueError:
            logger.warning("Invalid entry_id in callback data: %s", entry_id_str)
            await query.edit_message_text("Некорректный идентификатор записи.")
            return
        with SessionLocal() as session:
            existing_entry: Entry | None = session.get(Entry, entry_id)
            if existing_entry is None:
                await query.edit_message_text("Запись не найдена (уже удалена).")
                return
            user = update.effective_user
            if user is None:
                return
            assert user is not None
            if existing_entry.telegram_id != user.id:
                await query.edit_message_text(
                    "⚠️ Эта запись принадлежит другому пользователю."
                )
                return
            if action == "del":
                session.delete(existing_entry)
                if not commit(session):
                    await query.edit_message_text("⚠️ Не удалось удалить запись.")
                    return
                await query.edit_message_text("❌ Запись удалена.")
                return
            if action == "edit":
                user_data = context.user_data
                message = query.message
                if message is None:
                    return
                assert message is not None
                user_data["edit_entry"] = {
                    "id": existing_entry.id,
                    "chat_id": message.chat_id,
                    "message_id": message.message_id,
                }
                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "сахар",
                                callback_data=f"edit_field:{existing_entry.id}:sugar",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "xe", callback_data=f"edit_field:{existing_entry.id}:xe"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "dose", callback_data=f"edit_field:{existing_entry.id}:dose"
                            )
                        ],
                    ]
                )
                await query.edit_message_reply_markup(reply_markup=keyboard)
                return
    elif data.startswith("edit_field:"):
        try:
            _, entry_id_str, field = data.split(":")
            edit_entry_id = int(entry_id_str)
        except ValueError:
            logger.warning("Invalid edit_field data: %s", data)
            await query.edit_message_text("Некорректные данные для редактирования.")
            return
        user_data = context.user_data
        user_data["edit_id"] = edit_entry_id
        user_data["edit_field"] = field
        user_data["edit_query"] = query
        prompt = {
            "sugar": "Введите уровень сахара (ммоль/л).",
            "xe": "Введите количество ХЕ.",
            "dose": "Введите дозу инсулина (ед.).",
        }.get(field, "Введите значение")
        message = query.message
        if message is None:
            return
        assert message is not None
        await message.reply_text(prompt, reply_markup=ForceReply(selective=True))
        return
    else:
        logger.warning("Unrecognized callback data: %s", data)
        await query.edit_message_text("Команда не распознана")

