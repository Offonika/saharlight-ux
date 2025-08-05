"""Handlers for personal reminders."""

from __future__ import annotations

from datetime import time, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from diabetes.db import SessionLocal, Reminder, ReminderLog
from .common_handlers import commit_session

MAX_REMINDERS = 5

# Map reminder type codes to display names
REMINDER_NAMES = {
    "sugar": "Сахар",  # noqa: RUF001
    "long_insulin": "Длинный инсулин",  # noqa: RUF001
    "medicine": "Лекарство",  # noqa: RUF001
    "xe_after": "Проверить ХЕ после еды",  # noqa: RUF001
}

# Conversation states
REMINDER_TYPE, REMINDER_VALUE = range(2)


def _describe(rem: Reminder) -> str:
    if rem.type == "sugar":
        if rem.time:
            return f"Замерить сахар {rem.time}"
        return f"Замерить сахар каждые {rem.interval_hours} ч"
    if rem.type == "long_insulin":
        return f"Длинный инсулин {rem.time}"
    if rem.type == "medicine":
        return f"Таблетки/лекарство {rem.time}"
    if rem.type == "xe_after":
        return f"Проверить ХЕ через {rem.minutes_after} мин"
    return rem.type


def schedule_reminder(rem: Reminder, job_queue) -> None:
    name = f"reminder_{rem.id}"
    if rem.type in {"sugar", "long_insulin", "medicine"}:
        if rem.time:
            hh, mm = map(int, rem.time.split(":"))
            job_queue.run_daily(
                reminder_job,
                time=time(hour=hh, minute=mm),
                data={"reminder_id": rem.id, "chat_id": rem.telegram_id},
                name=name,
            )
        elif rem.interval_hours:
            job_queue.run_repeating(
                reminder_job,
                interval=timedelta(hours=rem.interval_hours),
                data={"reminder_id": rem.id, "chat_id": rem.telegram_id},
                name=name,
            )
    # xe_after reminders are scheduled when entry is logged


def schedule_all(job_queue) -> None:
    with SessionLocal() as session:
        reminders = session.query(Reminder).all()
    for rem in reminders:
        schedule_reminder(rem, job_queue)


async def reminders_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    with SessionLocal() as session:
        rems = session.query(Reminder).filter_by(telegram_id=user_id).all()
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("➕ Добавить", callback_data="add_reminder")]]
    )
    if not rems:
        await update.message.reply_text(
            "У вас нет напоминаний. Нажмите кнопку ниже или отправьте /addreminder.",
            reply_markup=keyboard,
        )
        return
    lines = [f"{r.id}. {_describe(r)}" for r in rems]
    text = (
        "Ваши напоминания (нажмите кнопку ниже, чтобы добавить новое):\n"
        + "\n".join(lines)
    )
    await update.message.reply_text(text, reply_markup=keyboard)


async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a reminder using command arguments."""
    user_id = update.effective_user.id
    args = getattr(context, "args", [])
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: /addreminder <type> <value>"  # noqa: RUF001
        )
        return
    rtype, value = args[0], args[1]
    reminder = Reminder(telegram_id=user_id, type=rtype)
    if rtype == "sugar":
        if ":" in value:
            reminder.time = value
        else:
            try:
                reminder.interval_hours = int(value)
            except ValueError:
                await update.message.reply_text("Интервал должен быть числом.")
                return
    elif rtype in {"long_insulin", "medicine"}:
        reminder.time = value
    elif rtype == "xe_after":
        try:
            reminder.minutes_after = int(value)
        except ValueError:
            await update.message.reply_text("Значение должно быть числом.")
            return
    else:
        await update.message.reply_text("Неизвестный тип напоминания.")
        return

    with SessionLocal() as session:
        count = session.query(Reminder).filter_by(telegram_id=user_id).count()
        if count >= MAX_REMINDERS:
            await update.message.reply_text(
                "Можно создать не более 5 напоминаний."  # noqa: RUF001
            )
            return
        session.add(reminder)
        if not commit_session(session):
            await update.message.reply_text(
                "⚠️ Не удалось сохранить напоминание."
            )
            return
        rid = reminder.id

    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    schedule_reminder(reminder, context.job_queue)
    await update.message.reply_text(f"Сохранено: {_describe(reminder)}")


async def add_reminder_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start reminder creation and ask for type."""
    user_id = update.effective_user.id
    query = getattr(update, "callback_query", None)
    message = update.message or (query.message if query else None)
    if query:
        await query.answer()
    with SessionLocal() as session:
        count = session.query(Reminder).filter_by(telegram_id=user_id).count()
    if count >= MAX_REMINDERS:
        await message.reply_text("Можно создать не более 5 напоминаний.")
        return ConversationHandler.END
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    REMINDER_NAMES["sugar"], callback_data="rem_type:sugar"
                ),
                InlineKeyboardButton(
                    REMINDER_NAMES["long_insulin"],
                    callback_data="rem_type:long_insulin",
                ),
            ],
            [
                InlineKeyboardButton(
                    REMINDER_NAMES["medicine"], callback_data="rem_type:medicine"
                ),
                InlineKeyboardButton(
                    REMINDER_NAMES["xe_after"], callback_data="rem_type:xe_after"
                ),
            ],
        ]
    )
    await message.reply_text(
        "Выберите тип напоминания:", reply_markup=keyboard
    )
    return REMINDER_TYPE


async def add_reminder_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Store chosen reminder type and prompt for value."""
    query = update.callback_query
    await query.answer()
    rtype = query.data.split(":", 1)[1]
    context.user_data["rem_type"] = rtype
    rname = REMINDER_NAMES.get(rtype, rtype)
    if rtype == "sugar":
        prompt = (
            f"Вы выбрали {rname}. Введите время ЧЧ:ММ или интервал в часах."  # noqa: RUF001
        )
    elif rtype in {"long_insulin", "medicine"}:
        prompt = f"Вы выбрали {rname}. Введите время ЧЧ:ММ."
    else:
        prompt = (
            f"Вы выбрали {rname}. Введите минуты после еды."  # noqa: RUF001
        )
    await query.message.reply_text(prompt)
    return REMINDER_VALUE


async def add_reminder_value(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Validate user input, save reminder and schedule it."""
    rtype = context.user_data.get("rem_type")
    value = update.message.text.strip()
    user_id = update.effective_user.id
    reminder = Reminder(telegram_id=user_id, type=rtype)
    if rtype == "sugar":
        if ":" in value:
            reminder.time = value
        else:
            try:
                reminder.interval_hours = int(value)
            except ValueError:
                await update.message.reply_text("Интервал должен быть числом.")
                return REMINDER_VALUE
    elif rtype in {"long_insulin", "medicine"}:
        reminder.time = value
    elif rtype == "xe_after":
        try:
            reminder.minutes_after = int(value)
        except ValueError:
            await update.message.reply_text("Значение должно быть числом.")
            return REMINDER_VALUE

    with SessionLocal() as session:
        count = (
            session.query(Reminder).filter_by(telegram_id=user_id).count()
        )
        if count >= MAX_REMINDERS:
            await update.message.reply_text(
                "Можно создать не более 5 напоминаний."
            )
            return ConversationHandler.END
        session.add(reminder)
        if not commit_session(session):
            await update.message.reply_text(
                "⚠️ Не удалось сохранить напоминание."
            )
            return ConversationHandler.END
        rid = reminder.id

    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    schedule_reminder(reminder, context.job_queue)
    context.user_data.pop("rem_type", None)
    await update.message.reply_text(f"Сохранено: {_describe(reminder)}")
    return ConversationHandler.END


async def add_reminder_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel reminder creation."""
    await update.message.reply_text("Отменено.")
    context.user_data.pop("rem_type", None)
    return ConversationHandler.END


add_reminder_conv = ConversationHandler(
    entry_points=[
        CommandHandler("addreminder", add_reminder_start),
        CallbackQueryHandler(add_reminder_start, pattern="^add_reminder$")
    ],
    states={
        REMINDER_TYPE: [CallbackQueryHandler(add_reminder_type, pattern="^rem_type:")],
        REMINDER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_value)],
    },
    fallbacks=[CommandHandler("cancel", add_reminder_cancel)],
    per_message=False,
)


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message or (update.callback_query.message if update.callback_query else None)
    args = getattr(context, "args", [])
    if not args:
        if message:
            await message.reply_text("Укажите ID: /delreminder <id>")
        return
    try:
        rid = int(args[0])
    except ValueError:
        if message:
            await message.reply_text("ID должен быть числом: /delreminder <id>")
        return
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem:
            if message:
                await message.reply_text("Не найдено")
            return
        session.delete(rem)
        commit_session(session)
    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    if message:
        await message.reply_text("Удалено")


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    rid = data["reminder_id"]
    chat_id = data["chat_id"]
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem:
            return
        session.add(
            ReminderLog(reminder_id=rid, telegram_id=chat_id, action="trigger")
        )
        commit_session(session)
        text = _describe(rem)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Отложить 10 мин", callback_data=f"remind_snooze:{rid}"
                ),
                InlineKeyboardButton("Отмена", callback_data=f"remind_cancel:{rid}"),
            ]
        ]
    )
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)


async def reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action, rid_str = query.data.split(":")
    rid = int(rid_str)
    chat_id = update.effective_user.id
    with SessionLocal() as session:
        session.add(
            ReminderLog(reminder_id=rid, telegram_id=chat_id, action=action)
        )
        commit_session(session)
    if action == "remind_snooze":
        context.job_queue.run_once(
            reminder_job,
            when=timedelta(minutes=10),
            data={"reminder_id": rid, "chat_id": chat_id},
            name=f"reminder_{rid}",
        )
        await query.edit_message_text("⏰ Отложено на 10 минут")
    else:
        await query.edit_message_text("❌ Напоминание отменено")


def schedule_after_meal(user_id: int, job_queue) -> None:
    with SessionLocal() as session:
        rems = (
            session.query(Reminder)
            .filter_by(telegram_id=user_id, type="xe_after")
            .all()
        )
    for rem in rems:
        job_queue.run_once(
            reminder_job,
            when=timedelta(minutes=rem.minutes_after),
            data={"reminder_id": rem.id, "chat_id": user_id},
            name=f"reminder_{rem.id}",
        )
