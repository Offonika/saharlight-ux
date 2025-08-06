"""Handlers for personal reminders."""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta
import logging

from diabetes.utils import parse_time_interval

from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest

from diabetes.db import Reminder, ReminderLog, SessionLocal, User
from .common_handlers import commit_session

logger = logging.getLogger(__name__)

PLAN_LIMITS = {"free": 5, "pro": 10}

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

def _limit_for(user: User | None) -> int:
    plan = getattr(user, "plan", "free")
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

# Conversation states
# Two-step wizard: choose type -> ask time
REMINDER_TYPE, REMINDER_TIME = range(2)


def _describe(rem: Reminder) -> str:
    """Return human readable reminder description with status and schedule."""

    status = "🔔" if rem.is_enabled else "🔕"
    action = REMINDER_ACTIONS.get(rem.type, rem.type)
    type_icon, schedule = _schedule_with_next(rem)
    return f"{status} {action} {type_icon} {schedule}".strip()


def _schedule_with_next(rem: Reminder) -> tuple[str, str]:
    """Return type icon and schedule string with next run time."""

    now = datetime.now()
    next_dt: datetime | None
    if rem.time:
        type_icon = "⏰"
        hh, mm = map(int, rem.time.split(":"))
        next_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if next_dt <= now:
            next_dt += timedelta(days=1)
        base = rem.time
    elif rem.interval_hours:
        type_icon = "⏱"
        next_dt = now + timedelta(hours=rem.interval_hours)
        base = f"q {rem.interval_hours} ч"
    elif rem.minutes_after:
        type_icon = "📸"
        next_dt = now + timedelta(minutes=rem.minutes_after)
        base = f"{rem.minutes_after} мин"
    else:
        type_icon = "🕘"
        next_dt = None
        base = ""

    if next_dt:
        if next_dt.date() == now.date():
            next_str = next_dt.strftime("%H:%M")
        else:
            next_str = next_dt.strftime("%d.%m %H:%M")
        schedule = f"{base} (next {next_str})" if base else f"next {next_str}"
    else:
        schedule = base
    return type_icon, schedule




def _render_reminders(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    with SessionLocal() as session:
        rems = session.query(Reminder).filter_by(telegram_id=user_id).all()
        user = session.query(User).filter_by(telegram_id=user_id).first()
    limit = _limit_for(user)
    active_count = sum(1 for r in rems if r.is_enabled)
    header = f"Ваши напоминания  ({active_count} / {limit} 🔔)"
    if active_count > limit:
        header += " ⚠️"
    add_button = [InlineKeyboardButton("➕ Добавить", callback_data="add_new")]
    if not rems:
        text = (
            header
            + "\nУ вас нет напоминаний. Нажмите кнопку ниже или отправьте /addreminder."
        )
        return text, InlineKeyboardMarkup([add_button])

    by_time: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_interval: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_photo: list[tuple[str, list[InlineKeyboardButton]]] = []

    for r in rems:
        title = _describe(r)
        if not r.is_enabled:
            title = f"<s>{title}</s>"
        line = f"{r.id}. {title}"
        status_icon = "🔔" if r.is_enabled else "🔕"
        row = [
            InlineKeyboardButton("✏️", callback_data=f"rem_edit:{r.id}"),
            InlineKeyboardButton("🗑️", callback_data=f"rem_del:{r.id}"),
            InlineKeyboardButton(status_icon, callback_data=f"rem_toggle:{r.id}"),
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
    extend("📸 Триггер-фото", by_photo)

    buttons.append(add_button)
    text = header + "\n" + "\n".join(lines)
    return text, InlineKeyboardMarkup(buttons)


def schedule_reminder(rem: Reminder, job_queue) -> None:
    if not rem.is_enabled:
        logger.debug(
            "Reminder %s disabled, skipping (type=%s, time=%s, interval=%s, minutes_after=%s)",
            rem.id,
            rem.type,
            rem.time,
            rem.interval_hours,
            rem.minutes_after,
        )
        return
    name = f"reminder_{rem.id}"
    for job in job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    if rem.type in {"sugar", "long_insulin", "medicine"}:
        if rem.time:
            hh, mm = map(int, rem.time.split(":"))
            logger.debug(
                "Adding job for reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
                rem.id,
                rem.type,
                rem.time,
                rem.interval_hours,
                rem.minutes_after,
            )
            job_queue.run_daily(
                reminder_job,
                time=time(hour=hh, minute=mm),
                data={"reminder_id": rem.id, "chat_id": rem.telegram_id},
                name=name,
            )
        elif rem.interval_hours:
            logger.debug(
                "Adding job for reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
                rem.id,
                rem.type,
                rem.time,
                rem.interval_hours,
                rem.minutes_after,
            )
            job_queue.run_repeating(
                reminder_job,
                interval=timedelta(hours=rem.interval_hours),
                data={"reminder_id": rem.id, "chat_id": rem.telegram_id},
                name=name,
            )
    # xe_after reminders are scheduled when entry is logged
    logger.debug(
        "Finished scheduling reminder %s (type=%s, time=%s, interval=%s, minutes_after=%s)",
        rem.id,
        rem.type,
        rem.time,
        rem.interval_hours,
        rem.minutes_after,
    )


def schedule_all(job_queue) -> None:
    if job_queue is None:
        logger.warning("schedule_all called without job_queue")
        return
    with SessionLocal() as session:
        reminders = session.query(Reminder).all()
    count = len(reminders)
    logger.debug("Found %d reminders to schedule", count)
    for rem in reminders:
        schedule_reminder(rem, job_queue)
    logger.debug("Scheduled %d reminders", count)


async def reminders_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text, keyboard = _render_reminders(user_id)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


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
        limit = _limit_for(user)
        if count >= limit:
            await update.message.reply_text(
                f"У вас уже {count} активных из {limit}. "
                "Отключите одно или Апгрейд до Pro, чтобы поднять лимит до 10",
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
    """Start reminder creation and ask what to remind."""
    user_id = update.effective_user.id
    query = getattr(update, "callback_query", None)
    message = update.message or (query.message if query else None)
    if query:
        await query.answer()
    with SessionLocal() as session:
        count = (
            session.query(Reminder)
            .filter_by(telegram_id=user_id, is_enabled=True)
            .count()
        )
        user = session.get(User, user_id)
        plan = getattr(user, "plan", "free").lower()
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    if count >= limit:
        await message.reply_text(
            f"У вас уже {limit} активных (лимит {plan.upper()}). "
            "Отключите одно или откройте PRO.",
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
            ],
            [InlineKeyboardButton("Отмена", callback_data="cancel")],
        ]
    )
    await message.reply_text("Что напомнить?", reply_markup=keyboard)
    return REMINDER_TYPE


async def add_reminder_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Store chosen reminder type and prompt for time."""
    query = update.callback_query
    await query.answer()
    rtype = query.data.split(":", 1)[1]
    context.user_data["rem_type"] = rtype
    context.user_data["cbq_id"] = query.id
    await query.message.reply_text(
        "Когда?", reply_markup=ForceReply(selective=True)
    )
    return REMINDER_TIME


async def add_reminder_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Validate time/interval and create reminder."""
    rtype = context.user_data.get("rem_type")
    text = update.message.text.strip()
    try:
        parsed = parse_time_interval(text)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return REMINDER_TIME
    if isinstance(parsed, time):
        time_str = parsed.strftime("%H:%M")
        interval_hours = None
    else:
        time_str = None
        interval_hours = int(parsed.total_seconds() // 3600)
    if rtype in {"long_insulin", "medicine"} and isinstance(parsed, timedelta):
        await update.message.reply_text("Только формат ЧЧ:ММ")
        return REMINDER_TIME
    user_id = update.effective_user.id
    with SessionLocal() as session:
        count = (
            session.query(Reminder)
            .filter_by(telegram_id=user_id, is_enabled=True)
            .count()
        )
        user = session.get(User, user_id)
        plan = getattr(user, "plan", "free").lower()
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        if count >= limit:
            await update.message.reply_text(
                f"У вас уже {limit} активных (лимит {plan.upper()}). "
                "Отключите одно или откройте PRO.",
            )
            context.user_data.pop("rem_type", None)
            return ConversationHandler.END
        reminder = Reminder(
            telegram_id=user_id,
            type=rtype,
            time=time_str,
            interval_hours=interval_hours,
            is_enabled=True,
        )
        session.add(reminder)
        if not commit_session(session):
            await update.message.reply_text(
                "⚠️ Не удалось сохранить напоминание."
            )
            return ConversationHandler.END
        session.refresh(reminder)
    schedule_reminder(reminder, context.job_queue)
    _, schedule = _schedule_with_next(reminder)
    match = re.search(r"(\d{2}:\d{2})", schedule)
    next_str = match.group(1) if match else ""
    cbq_id = context.user_data.pop("cbq_id", None)
    if cbq_id:
        await context.bot.answer_callback_query(
            cbq_id, text=f"Напоминание добавлено (next {next_str})"
        )
    context.user_data.pop("rem_type", None)
    return ConversationHandler.END


async def add_reminder_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Cancel reminder creation."""
    query = getattr(update, "callback_query", None)
    if query:
        await query.answer("Отменено")
    else:
        await update.message.reply_text("Отменено.")
    context.user_data.pop("rem_type", None)
    context.user_data.pop("cbq_id", None)
    context.user_data.pop("edit_reminder_id", None)
    context.user_data.pop("pending_value", None)
    context.user_data.pop("reminders_msg", None)
    return ConversationHandler.END


async def _photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .dose_handlers import _cancel_then, photo_prompt

    handler = _cancel_then(photo_prompt)
    return await handler(update, context)


add_reminder_conv = ConversationHandler(
    entry_points=[
        CommandHandler("addreminder", add_reminder_start),
        CallbackQueryHandler(add_reminder_start, pattern="^add_new$"),
    ],
    states={
        REMINDER_TYPE: [
            CallbackQueryHandler(add_reminder_type, pattern="^rem_type:"),
            CallbackQueryHandler(add_reminder_cancel, pattern="^cancel$"),
        ],
        REMINDER_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder_time)
        ],
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
        try:
            await query.edit_message_text("⏰ Отложено на 10 минут")
        except BadRequest as exc:
            if "Message is not modified" in str(exc):
                await query.answer()
            else:
                raise
    else:
        try:
            await query.edit_message_text("❌ Напоминание отменено")
        except BadRequest as exc:
            if "Message is not modified" in str(exc):
                await query.answer()
            else:
                raise


async def reminder_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    action_raw, rid_str = query.data.split(":", 1)
    if not action_raw.startswith("rem_"):
        await query.answer("Некорректное действие", show_alert=True)
        return
    action = action_raw.removeprefix("rem_")
    try:
        rid = int(rid_str)
    except ValueError:
        await query.answer("Некорректный ID", show_alert=True)
        return
    user_id = update.effective_user.id
    if action == "edit":
        context.user_data["edit_reminder_id"] = rid
        context.user_data["reminders_msg"] = query.message
        await query.message.reply_text(
            "Введите новое время ЧЧ:ММ или новый интервал (5h / 3d)",
            reply_markup=ForceReply(selective=True),
        )
        await query.answer("Готово ✅")
        return

    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            await query.answer("Не найдено", show_alert=True)
            return
        if action == "del":
            session.delete(rem)
        elif action == "toggle":
            rem.is_enabled = not rem.is_enabled
        commit_session(session)
        if action != "del":
            session.refresh(rem)

    if action == "toggle":
        if rem.is_enabled:
            schedule_reminder(rem, context.job_queue)
        else:
            for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
                job.schedule_removal()
    elif action == "del":
        for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
            job.schedule_removal()

    if action in {"del", "toggle"}:
        text, keyboard = _render_reminders(user_id)
        try:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except BadRequest as exc:
            if "Message is not modified" in str(exc):
                await query.answer()
            else:
                raise
        else:
            await query.answer("Готово ✅")


async def reminder_edit_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rid = context.user_data.get("edit_reminder_id")
    msg = context.user_data.get("reminders_msg")
    if not rid or not msg:
        return
    text = update.message.text.strip()
    try:
        parsed = parse_time_interval(text)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return
    user_id = update.effective_user.id
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            await update.message.reply_text("Не найдено")
            return
        if isinstance(parsed, time):
            rem.time = parsed.strftime("%H:%M")
            rem.interval_hours = None
        else:
            rem.time = None
            rem.interval_hours = int(parsed.total_seconds() // 3600)
        commit_session(session)
        session.refresh(rem)
    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    schedule_reminder(rem, context.job_queue)
    text_list, keyboard = _render_reminders(user_id)
    try:
        await msg.edit_text(text_list, reply_markup=keyboard, parse_mode="HTML")
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            pass
        else:
            raise
    context.user_data.pop("edit_reminder_id", None)
    context.user_data.pop("reminders_msg", None)


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


reminder_action_handler = CallbackQueryHandler(
    reminder_action_cb, pattern="^rem_(edit|del|toggle):"
)
reminder_edit_handler = MessageHandler(
    filters.REPLY & filters.Regex(r"^([0-9]{1,2}:[0-9]{2}|[0-9]+[hd])$"), reminder_edit_reply
)
