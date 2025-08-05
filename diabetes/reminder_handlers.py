"""Handlers for personal reminders."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from diabetes.db import SessionLocal, Reminder, ReminderLog, User
from .common_handlers import commit_session
 
MAX_REMINDERS = 5
PRO_REMINDERS = 10

# Map reminder type codes to display names
REMINDER_NAMES = {
    "sugar": "Сахар",  # noqa: RUF001
    "long_insulin": "Длинный инсулин",  # noqa: RUF001
    "medicine": "Лекарство",  # noqa: RUF001
    "xe_after": "Проверить ХЕ после еды",  # noqa: RUF001
}

REMINDER_ACTIONS = {
    "sugar": "Замерить сахар",  # noqa: RUF001
    "long_insulin": "Длинный инсулин",  # noqa: RUF001
    "medicine": "Таблетки/лекарство",  # noqa: RUF001
    "xe_after": "Проверить ХЕ",  # noqa: RUF001
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


def _schedule_with_next(rem: Reminder) -> str:
    """Return schedule string with next run time."""
    now = datetime.now()
    next_dt: datetime | None
    if rem.time:
        hh, mm = map(int, rem.time.split(":"))
        next_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if next_dt <= now:
            next_dt += timedelta(days=1)
        base = rem.time
    elif rem.interval_hours:
        next_dt = now + timedelta(hours=rem.interval_hours)
        base = f"q {rem.interval_hours} ч"
    elif rem.minutes_after:
        next_dt = now + timedelta(minutes=rem.minutes_after)
        base = f"{rem.minutes_after} мин"
    else:
        next_dt = None
        base = ""
    if next_dt:
        return f"{base} (след. — {next_dt:%H:%M})"  # noqa: RUF001
    return base


def _format_reminder_line(rem: Reminder) -> str:
    action = REMINDER_ACTIONS.get(rem.type, rem.type)
    schedule = _schedule_with_next(rem)
    return f"{action} {schedule}".strip()


def _render_reminders(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    with SessionLocal() as session:
        rems = session.query(Reminder).filter_by(telegram_id=user_id).all()
    add_button = [InlineKeyboardButton("➕ Добавить", callback_data="add_reminder")]
    if not rems:
        text = (
            "У вас нет напоминаний. Нажмите кнопку ниже или отправьте /addreminder."
        )
        return text, InlineKeyboardMarkup([add_button])

    by_time: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_interval: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_photo: list[tuple[str, list[InlineKeyboardButton]]] = []

    for r in rems:
        icon = "🔔" if r.is_enabled else "🔕"
        line = f"{icon} {r.id}. {_format_reminder_line(r)}"
        row = [
            InlineKeyboardButton("✏️", callback_data=f"edit:{r.id}"),
            InlineKeyboardButton("🗑️", callback_data=f"del:{r.id}"),
            InlineKeyboardButton(icon, callback_data=f"toggle:{r.id}"),
        ]
        if r.time:
            by_time.append((line, row))
        elif r.interval_hours:
            by_interval.append((line, row))
        else:
            by_photo.append((line, row))

    lines: list[str] = []
    buttons: list[list[InlineKeyboardButton]] = []

    def extend(section: str, items: list[tuple[str, list[InlineKeyboardButton]]]) -> None:
        if not items:
            return
        if lines:
            lines.append("")
        lines.append(section)
        for line_text, b in items:
            lines.append(line_text)
            buttons.append(b)

    extend("⏰ По времени", by_time)
    extend("⏱ Интервал", by_interval)
    extend("📸 После фото", by_photo)

    buttons.append(add_button)
    text = "Ваши напоминания:\n" + "\n".join(lines)
    return text, InlineKeyboardMarkup(buttons)


def schedule_reminder(rem: Reminder, job_queue) -> None:
    if not rem.is_enabled:
        return
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
    text, keyboard = _render_reminders(user_id)
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
        user = session.get(User, user_id)
        limit = (
            PRO_REMINDERS
            if getattr(user, "plan", "free") == "pro"
            else MAX_REMINDERS
        )
        if count >= limit:
            await update.message.reply_text(
                f"У вас уже {count} активных из {limit}. "
                "Отключите одно или перейдите на Pro, чтобы поднять лимит до 10",
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
        user = session.get(User, user_id)
    limit = (
        PRO_REMINDERS if getattr(user, "plan", "free") == "pro" else MAX_REMINDERS
    )
    if count >= limit:
        await message.reply_text(
            f"У вас уже {count} активных из {limit}. "
            "Отключите одно или перейдите на Pro, чтобы поднять лимит до 10",
        )
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


async def edit_reminder(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle callback to edit existing reminder."""
    query = update.callback_query
    rid_str = query.data.split(":", 1)[1]
    try:
        rid = int(rid_str)
    except ValueError:
        await query.answer("Некорректный ID", show_alert=True)
        return ConversationHandler.END
    user_id = update.effective_user.id
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            await query.answer("Не найдено", show_alert=True)
            return ConversationHandler.END
        rtype = rem.type
    context.user_data["rem_type"] = rtype
    context.user_data["edit_reminder_id"] = rid
    context.user_data["reminders_msg"] = query.message
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
    await query.answer()
    return REMINDER_VALUE


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
    edit_id = context.user_data.get("edit_reminder_id")

    if edit_id:
        with SessionLocal() as session:
            rem = session.get(Reminder, edit_id)
            if not rem or rem.telegram_id != user_id:
                await update.message.reply_text("Не найдено")
                context.user_data.pop("rem_type", None)
                context.user_data.pop("edit_reminder_id", None)
                context.user_data.pop("reminders_msg", None)
                return ConversationHandler.END
            if rtype == "sugar":
                if ":" in value:
                    rem.time = value
                    rem.interval_hours = None
                else:
                    try:
                        rem.interval_hours = int(value)
                        rem.time = None
                    except ValueError:
                        await update.message.reply_text("Интервал должен быть числом.")
                        return REMINDER_VALUE
            elif rtype in {"long_insulin", "medicine"}:
                rem.time = value
            elif rtype == "xe_after":
                try:
                    rem.minutes_after = int(value)
                except ValueError:
                    await update.message.reply_text("Значение должно быть числом.")
                    return REMINDER_VALUE
            commit_session(session)
            session.refresh(rem)
        for job in context.job_queue.get_jobs_by_name(f"reminder_{edit_id}"):
            job.schedule_removal()
        schedule_reminder(rem, context.job_queue)
        context.user_data.pop("rem_type", None)
        context.user_data.pop("edit_reminder_id", None)
        msg = context.user_data.pop("reminders_msg", None)
        if msg:
            text, keyboard = _render_reminders(user_id)
            await msg.edit_text(text, reply_markup=keyboard)
        await update.message.reply_text(f"Обновлено: {_describe(rem)}")
        return ConversationHandler.END

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
        count = session.query(Reminder).filter_by(telegram_id=user_id).count()
        user = session.get(User, user_id)
        limit = (
            PRO_REMINDERS
            if getattr(user, "plan", "free") == "pro"
            else MAX_REMINDERS
        )
        if count >= limit:
            await update.message.reply_text(
                f"У вас уже {count} активных из {limit}. "
                "Отключите одно или перейдите на Pro, чтобы поднять лимит до 10",
            )
            return ConversationHandler.END
        session.add(reminder)
        if not commit_session(session):
            await update.message.reply_text(
                "⚠️ Не удалось сохранить напоминание.",
            )
            return ConversationHandler.END
        rid = reminder.id

    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    schedule_reminder(reminder, context.job_queue)
    context.user_data.pop("rem_type", None)
    await update.message.reply_text(
        f"Сохранено: {_describe(reminder)}. "
        "Отправьте /addreminder, чтобы добавить ещё.",
    )
    return ConversationHandler.END
async def add_reminder_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancel reminder creation."""
    await update.message.reply_text("Отменено.")
    context.user_data.pop("rem_type", None)
    return ConversationHandler.END


async def _photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .dose_handlers import _cancel_then, photo_prompt

    handler = _cancel_then(photo_prompt)
    return await handler(update, context)


add_reminder_conv = ConversationHandler(
    entry_points=[
        CommandHandler("addreminder", add_reminder_start),
        CallbackQueryHandler(add_reminder_start, pattern="^add_reminder$"),
        CallbackQueryHandler(edit_reminder, pattern="^edit:")
    ],
    states={
        REMINDER_TYPE: [CallbackQueryHandler(add_reminder_type, pattern="^rem_type:")],
        REMINDER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_value)],
    },
    fallbacks=[
        CommandHandler("cancel", add_reminder_cancel),
        MessageHandler(filters.Regex("^📷 Фото еды$"), _photo_fallback),
    ],
    per_message=False,
    allow_reentry=True,
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


async def delete_reminder_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    rid_str = query.data.split(":", 1)[1]
    try:
        rid = int(rid_str)
    except ValueError:
        await query.answer("Некорректный ID", show_alert=True)
        return
    user_id = update.effective_user.id
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            await query.answer("Не найдено", show_alert=True)
            return
        session.delete(rem)
        commit_session(session)
    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    text, keyboard = _render_reminders(user_id)
    await query.edit_message_text(text, reply_markup=keyboard)
    await query.answer("Удалено")


async def toggle_reminder_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    rid_str = query.data.split(":", 1)[1]
    try:
        rid = int(rid_str)
    except ValueError:
        await query.answer("Некорректный ID", show_alert=True)
        return
    user_id = update.effective_user.id
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            await query.answer("Не найдено", show_alert=True)
            return
        rem.is_enabled = not rem.is_enabled
        commit_session(session)
        session.refresh(rem)
    if rem.is_enabled:
        schedule_reminder(rem, context.job_queue)
        for_text = "🔔 Включено"
    else:
        for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
            job.schedule_removal()
        for_text = "🔕 Отключено"
    text, keyboard = _render_reminders(user_id)
    await query.edit_message_text(text, reply_markup=keyboard)
    await query.answer(for_text)


def schedule_after_meal(user_id: int, job_queue) -> None:
    with SessionLocal() as session:
        rems = (
            session.query(Reminder)
            .filter_by(telegram_id=user_id, type="xe_after", is_enabled=True)
            .all()
        )
    for rem in rems:
        job_queue.run_once(
            reminder_job,
            when=timedelta(minutes=rem.minutes_after),
            data={"reminder_id": rem.id, "chat_id": user_id},
            name=f"reminder_{rem.id}",
        )
