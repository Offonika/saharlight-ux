from __future__ import annotations

import logging
from typing import Any

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services.api.app.diabetes.services.db import Entry
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.ui import menu_keyboard

from .db import SessionLocal

logger = logging.getLogger(__name__)


async def handle_confirm_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Persist a pending entry to the database."""
    context.user_data = context.user_data or {}
    query = update.callback_query
    await query.answer()
    entry_data: dict[str, Any] | None = context.user_data.pop("pending_entry", None)
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
        reminder_handlers.schedule_after_meal(update.effective_user.id, job_queue)


async def handle_edit_pending_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Prompt the user to edit a pending entry before saving."""
    context.user_data = context.user_data or {}
    query = update.callback_query
    await query.answer()
    entry_data: dict[str, Any] | None = context.user_data.get("pending_entry")
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


async def handle_cancel_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Cancel the pending entry editing."""
    context.user_data = context.user_data or {}
    query = update.callback_query
    await query.answer()
    context.user_data.pop("pending_entry", None)
    await query.edit_message_text("❌ Запись отменена.")
    await query.message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard)


async def handle_edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prepare editing of a saved diary entry."""
    context.user_data = context.user_data or {}
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    try:
        _, entry_id_str = data.split(":", 1)
        entry_id = int(entry_id_str)
    except ValueError:
        logger.warning("Invalid entry_id in callback data: %s", data)
        await query.edit_message_text("Некорректный идентификатор записи.")
        return
    with SessionLocal() as session:
        entry = session.get(Entry, entry_id)
        if not entry:
            await query.edit_message_text("Запись не найдена (уже удалена).")
            return
        if entry.telegram_id != update.effective_user.id:
            await query.edit_message_text("⚠️ Эта запись принадлежит другому пользователю.")
            return
        context.user_data["edit_entry"] = {
            "id": entry.id,
            "chat_id": query.message.chat_id,
            "message_id": query.message.message_id,
        }
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("сахар", callback_data=f"edit_field:{entry_id}:sugar")],
            [InlineKeyboardButton("xe", callback_data=f"edit_field:{entry_id}:xe")],
            [InlineKeyboardButton("dose", callback_data=f"edit_field:{entry_id}:dose")],
        ]
    )
    await query.edit_message_reply_markup(reply_markup=keyboard)


async def handle_delete_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a diary entry."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    try:
        _, entry_id_str = data.split(":", 1)
        entry_id = int(entry_id_str)
    except ValueError:
        logger.warning("Invalid entry_id in callback data: %s", data)
        await query.edit_message_text("Некорректный идентификатор записи.")
        return
    with SessionLocal() as session:
        entry = session.get(Entry, entry_id)
        if not entry:
            await query.edit_message_text("Запись не найдена (уже удалена).")
            return
        if entry.telegram_id != update.effective_user.id:
            await query.edit_message_text("⚠️ Эта запись принадлежит другому пользователю.")
            return
        session.delete(entry)
        if not commit(session):
            await query.edit_message_text("⚠️ Не удалось удалить запись.")
            return
    await query.edit_message_text("❌ Запись удалена.")


async def handle_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt for new value of a specific field."""
    context.user_data = context.user_data or {}
    query = update.callback_query
    await query.answer()
    data = query.data or ""
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
    prompts: dict[str, str] = {
        "sugar": "Введите уровень сахара (ммоль/л).",
        "xe": "Введите количество ХЕ.",
        "dose": "Введите дозу инсулина (ед.).",
    }
    prompt = prompts.get(field, "Введите значение")
    await query.message.reply_text(prompt, reply_markup=ForceReply(selective=True))


async def handle_unknown_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Fallback handler for unexpected callback data."""
    query = update.callback_query
    await query.answer()
    data = (query.data or "")
    if data.startswith("rem_"):
        return
    logger.warning("Unrecognized callback data: %s", data)
    await query.edit_message_text("Команда не распознана")


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch callbacks to individual handlers.

    This function is kept for backward compatibility and tests. In production
    handlers are registered directly with their own patterns.
    """
    data = (update.callback_query.data or "")
    if data == "confirm_entry":
        await handle_confirm_entry(update, context)
    elif data == "edit_entry":
        await handle_edit_pending_entry(update, context)
    elif data == "cancel_entry":
        await handle_cancel_entry(update, context)
    elif data.startswith("edit:"):
        await handle_edit_entry(update, context)
    elif data.startswith("del:"):
        await handle_delete_entry(update, context)
    elif data.startswith("edit_field:"):
        await handle_edit_field(update, context)
    else:
        await handle_unknown_callback(update, context)
