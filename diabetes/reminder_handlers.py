"""Handlers for personal reminders."""

from __future__ import annotations

from datetime import time, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from diabetes.db import SessionLocal, Reminder, ReminderLog
from .common_handlers import commit_session

MAX_REMINDERS = 5


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
    if not rems:
        await update.message.reply_text("У вас нет напоминаний.")
        return
    lines = [f"{r.id}. {_describe(r)}" for r in rems]
    await update.message.reply_text("\n".join(lines))


async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = getattr(context, "args", [])
    message = update.message or (update.callback_query.message if update.callback_query else None)
    if not args or len(args) < 2:
        if message:
            await message.reply_text(
                "Формат: /addreminder [id] <type> <time|interval>",
            )
        return
    idx = 0
    rtype: str
    val: str
    with SessionLocal() as session:
        if args[0].isdigit():
            rid = int(args[0])
            idx = 1
            reminder = session.get(Reminder, rid)
            if not reminder:
                if message:
                    await message.reply_text("Напоминание не найдено.")
                return
        else:
            reminder = None
        if len(args) <= idx + 1:
            if message:
                await message.reply_text(
                    "Формат: /addreminder [id] <type> <time|interval>",
                )
            return
        rtype = args[idx]
        val = args[idx + 1]
        if reminder is None:
            count = (
                session.query(Reminder)
                .filter_by(telegram_id=user_id)
                .count()
            )
            if count >= MAX_REMINDERS:
                if message:
                    await message.reply_text(
                        "Можно создать не более 5 напоминаний.",
                    )
                return
            reminder = Reminder(telegram_id=user_id, type=rtype)
            session.add(reminder)
        reminder.type = rtype
        reminder.time = None
        reminder.interval_hours = None
        reminder.minutes_after = None
        if rtype == "sugar":
            if ":" in val:
                reminder.time = val
            else:
                try:
                    reminder.interval_hours = int(val)
                except ValueError:
                    if message:
                        await message.reply_text("Интервал должен быть числом.")
                    return
        elif rtype in {"long_insulin", "medicine"}:
            reminder.time = val
        elif rtype == "xe_after":
            try:
                reminder.minutes_after = int(val)
            except ValueError:
                if message:
                    await message.reply_text("Значение должно быть числом.")
                return
        commit_session(session)
        rid = reminder.id
    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    schedule_reminder(reminder, context.job_queue)
    if message:
        await message.reply_text(f"Сохранено: {_describe(reminder)}")


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message or (update.callback_query.message if update.callback_query else None)
    args = getattr(context, "args", [])
    if not args:
        if message:
            await message.reply_text("Укажите ID: /delreminder <id>")
        return
    rid = int(args[0])
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
