from __future__ import annotations

import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ForceReply,
    Message,
    CallbackQuery,
)
from telegram.ext import ContextTypes
from typing import Awaitable, Callable, cast

from services.api.app.diabetes.services.db import Entry, SessionLocal
from services.api.app.ui.keyboard import build_main_keyboard

from services.api.app.diabetes.services.repository import CommitError, commit
from . import EntryData, UserData

logger = logging.getLogger(__name__)


Handler = Callable[
    [Update, ContextTypes.DEFAULT_TYPE, CallbackQuery, str], Awaitable[None]
]


async def handle_confirm_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: CallbackQuery, _: str
) -> None:
    """Save pending entry to DB, check alerts and schedule reminders."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return
    user_data = cast(UserData, user_data_raw)
    entry_data_raw = user_data.pop("pending_entry", None)
    if not isinstance(entry_data_raw, dict):
        await query.edit_message_text("❗ Нет данных для сохранения.")
        return
    entry_data: EntryData = entry_data_raw
    with SessionLocal() as session:
        # Filter out fields not defined in the ORM model to avoid TypeError
        allowed_keys = set(Entry.__table__.columns.keys())
        clean_data = {k: v for k, v in entry_data.items() if k in allowed_keys}
        entry = Entry(**clean_data)
        session.add(entry)
        try:
            commit(session)
        except CommitError:
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
        reminder_handlers.schedule_after_meal(user.id, job_queue)


async def handle_edit_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: CallbackQuery, _: str
) -> None:
    """Prompt user to resend data to update the pending entry."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return
    user_data = cast(UserData, user_data_raw)
    entry_data_raw = user_data.get("pending_entry")
    if not isinstance(entry_data_raw, dict):
        await query.edit_message_text("❗ Нет данных для редактирования.")
        return
    user_data["edit_id"] = None
    await query.edit_message_text(
        "Отправьте новое сообщение в формате:\n"
        "`сахар=<ммоль/л>  xe=<ХЕ>  carbs=<г>  dose=<ед>`\n"
        "Можно указывать не все поля (что прописано — то и поменяется).",
        parse_mode="Markdown",
    )


async def handle_cancel_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: CallbackQuery, _: str
) -> None:
    """Discard pending entry and show main menu keyboard."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return
    user_data = cast(UserData, user_data_raw)
    user_data.pop("pending_entry", None)
    await query.edit_message_text("❌ Запись отменена.")
    message = query.message
    if not isinstance(message, Message):
        return
    await message.reply_text(
        "📋 Выберите действие:", reply_markup=build_main_keyboard()
    )


async def handle_edit_or_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: CallbackQuery, data: str
) -> None:
    """Edit or delete an existing entry based on callback action."""
    if ":" not in data:
        logger.warning("Invalid callback data format: %s", data)
        await query.edit_message_text("Некорректный формат данных.")
        return
    try:
        action, entry_id_str = data.split(":", 1)
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
        if existing_entry.telegram_id != user.id:
            await query.edit_message_text(
                "⚠️ Эта запись принадлежит другому пользователю."
            )
            return
        if action == "del":
            session.delete(existing_entry)
            try:
                commit(session)
            except CommitError:
                await query.edit_message_text("⚠️ Не удалось удалить запись.")
                return
            await query.edit_message_text("❌ Запись удалена.")
            return
    if action != "edit":
        return
    user_data_raw = context.user_data
    if user_data_raw is None:
        return
    user_data = cast(UserData, user_data_raw)
    message = query.message
    if not isinstance(message, Message):
        return
    user_data["edit_entry"] = {
        "id": entry_id,
        "chat_id": message.chat_id,
        "message_id": message.message_id,
    }
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "сахар", callback_data=f"edit_field:{entry_id}:sugar"
                )
            ],
            [InlineKeyboardButton("xe", callback_data=f"edit_field:{entry_id}:xe")],
            [InlineKeyboardButton("dose", callback_data=f"edit_field:{entry_id}:dose")],
        ]
    )
    await query.edit_message_reply_markup(reply_markup=keyboard)


async def handle_edit_field(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: CallbackQuery, data: str
) -> None:
    """Request new value for a specific field during entry editing."""
    try:
        _, entry_id_str, field = data.split(":")
        edit_entry_id = int(entry_id_str)
    except ValueError:
        logger.warning("Invalid edit_field data: %s", data)
        await query.edit_message_text("Некорректные данные для редактирования.")
        return
    user_data_raw = context.user_data
    if user_data_raw is None:
        return
    user_data = cast(UserData, user_data_raw)
    user_data["edit_id"] = edit_entry_id
    user_data["edit_field"] = field
    user_data["edit_query"] = query
    prompt = {
        "sugar": "Введите уровень сахара (ммоль/л).",
        "xe": "Введите количество ХЕ.",
        "dose": "Введите дозу инсулина (ед.).",
    }.get(field, "Введите значение")
    message = query.message
    if not isinstance(message, Message):
        return
    await message.reply_text(prompt, reply_markup=ForceReply(selective=True))


async def profile_timezone_stub(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: CallbackQuery,
    _: str,
) -> None:
    """Placeholder handler for profile timezone callbacks."""
    return None


callback_handlers: dict[str, Handler] = {
    "confirm_entry": handle_confirm_entry,
    "edit_entry": handle_edit_entry,
    "cancel_entry": handle_cancel_entry,
    "edit_field:": handle_edit_field,
    "edit:": handle_edit_or_delete,
    "del:": handle_edit_or_delete,
    "profile_timezone": profile_timezone_stub,
}


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route callbacks for entry confirmation, editing and deletion."""
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    data = query.data or ""

    if data.startswith("rem_"):
        return

    handler = callback_handlers.get(data)
    if handler is not None:
        await handler(update, context, query, data)
        return

    if ":" in data:
        prefix = data.split(":", 1)[0] + ":"
        handler = callback_handlers.get(prefix)
        if handler is not None:
            await handler(update, context, query, data)
            return

    logger.warning("Unrecognized callback data: %s", data)
    await query.edit_message_text("Команда не распознана")
