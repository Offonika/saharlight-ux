"""Handlers for personal reminders."""

from __future__ import annotations

import datetime
from datetime import timedelta, time, timezone
from zoneinfo import ZoneInfo
import logging
import json
import re

from diabetes.utils import parse_time_interval

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest

from diabetes.db import Reminder, ReminderLog, SessionLocal, User, run_db
from .common_handlers import commit_session
from diabetes.config import WEBAPP_URL

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

def _describe(rem: Reminder, user: User | None = None) -> str:
    """Return human readable reminder description with status and schedule."""

    status = "🔔" if rem.is_enabled else "🔕"
    action = REMINDER_ACTIONS.get(rem.type, rem.type)
    type_icon, schedule = _schedule_with_next(rem, user)
    return f"{status} {action} {type_icon} {schedule}".strip()


def _schedule_with_next(rem: Reminder, user: User | None = None) -> tuple[str, str]:
    """Return type icon and schedule string with next run time."""

    dt_cls = getattr(datetime, "datetime", datetime)
    if user is None:
        user = rem.__dict__.get("user")
    tz = timezone.utc
    tzname = getattr(user, "timezone", None)
    if tzname:
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            pass
    try:
        now = dt_cls.now(tz)
    except TypeError:
        now = dt_cls.now().replace(tzinfo=tz)
    next_dt: datetime.datetime | None
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
        base = f"каждые {rem.interval_hours} ч"
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




def _render_reminders(
    session, user_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    rems = session.query(Reminder).filter_by(telegram_id=user_id).all()
    user = session.query(User).filter_by(telegram_id=user_id).first()
    limit = _limit_for(user)
    active_count = sum(1 for r in rems if r.is_enabled)
    header = f"Ваши напоминания  ({active_count} / {limit} 🔔)"
    if active_count > limit:
        header += " ⚠️"
    add_button_row: list[InlineKeyboardButton] | None = None
    if WEBAPP_URL:
        add_button_row = [
            InlineKeyboardButton(
                "➕ Добавить",
                web_app=WebAppInfo(f"{WEBAPP_URL}/reminders"),
            )
        ]
    if not rems:
        text = header
        if WEBAPP_URL:
            text += "\nУ вас нет напоминаний. Нажмите кнопку ниже или отправьте /addreminder."
            return text, InlineKeyboardMarkup([add_button_row])
        text += "\nУ вас нет напоминаний. Отправьте /addreminder."
        return text, InlineKeyboardMarkup([])

    by_time: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_interval: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_photo: list[tuple[str, list[InlineKeyboardButton]]] = []

    for r in rems:
        title = _describe(r, user)
        if not r.is_enabled:
            title = f"<s>{title}</s>"
        line = f"{r.id}. {title}"
        status_icon = "🔔" if r.is_enabled else "🔕"
        row: list[InlineKeyboardButton] = []
        if WEBAPP_URL:
            row.append(
                InlineKeyboardButton(
                    "✏️",
                    web_app=WebAppInfo(f"{WEBAPP_URL}/reminders?id={r.id}"),
                )
            )
        row.extend(
            [
                InlineKeyboardButton("🗑️", callback_data=f"rem_del:{r.id}"),
                InlineKeyboardButton(status_icon, callback_data=f"rem_toggle:{r.id}"),
            ]
        )
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

    if add_button_row:
        buttons.append(add_button_row)
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

    tz = timezone.utc
    user = rem.__dict__.get("user")
    if user is None or getattr(user, "timezone", None) is None:
        with SessionLocal() as session:
            user = session.get(User, rem.telegram_id)
    tzname = getattr(user, "timezone", None) if user else None
    if tzname:
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            pass

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
                time=time(hour=hh, minute=mm, tzinfo=tz),
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
    text, keyboard = await run_db(
        _render_reminders, user_id, sessionmaker=SessionLocal
    )
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

    def db_add(session):
        count = session.query(Reminder).filter_by(telegram_id=user_id).count()
        user = session.get(User, user_id)
        limit = _limit_for(user)
        if count >= limit:
            return "limit", user, limit, count
        session.add(reminder)
        if not commit_session(session):
            logger.error("Failed to commit new reminder for user %s", user_id)
            return "error", user, limit, count
        return "ok", user, limit, reminder.id

    status, user, limit, rid_or_count = await run_db(
        db_add, sessionmaker=SessionLocal
    )

    if status == "limit":
        count = rid_or_count
        await update.message.reply_text(
            f"У вас уже {count} активных из {limit}. "
            "Отключите одно или Апгрейд до Pro, чтобы поднять лимит до 10",
        )
        return
    if status == "error":
        await update.message.reply_text(
            "⚠️ Не удалось сохранить напоминание."
        )
        return

    rid = rid_or_count
    for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
        job.schedule_removal()
    schedule_reminder(reminder, context.job_queue)
    await update.message.reply_text(f"Сохранено: {_describe(reminder, user)}")


async def reminder_webapp_save(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Save reminder data sent from the web app."""
    raw = update.effective_message.web_app_data.data
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    rtype = data.get("type")
    raw_value = data.get("value")
    rid = data.get("id")
    if not rtype or raw_value is None:
        return
    value = str(raw_value).strip()
    if not value:
        return
    logger.debug("Received raw reminder value: %r", value)
    user_id = update.effective_user.id
    if rtype == "xe_after":
        try:
            minutes = int(value)
        except ValueError:
            await update.effective_message.reply_text("Неверный формат")
            return
        parsed = None
    else:
        if not re.fullmatch(r"\d{1,2}:\d{2}|\d+h", value):
            logger.warning("Invalid reminder value format: %s", value)
            await update.effective_message.reply_text(
                "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h."
            )
            return
        try:
            parsed = parse_time_interval(value)
        except ValueError:
            logger.warning("Failed to parse reminder value: %s", value)
            await update.effective_message.reply_text(
                "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h."
            )
            return
        minutes = None
    def db_save(session):
        if rid:
            rem = session.get(Reminder, int(rid))
            if not rem or rem.telegram_id != user_id:
                return "not_found", None, None, None
        else:
            count = (
                session.query(Reminder)
                .filter_by(telegram_id=user_id, is_enabled=True)
                .count()
            )
            user = session.get(User, user_id)
            plan = getattr(user, "plan", "free").lower()
            limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
            if count >= limit:
                return "limit", None, plan, limit
            rem = Reminder(telegram_id=user_id, type=rtype, is_enabled=True)
            session.add(rem)
        if rtype == "xe_after":
            rem.minutes_after = minutes
            rem.time = None
            rem.interval_hours = None
        else:
            rem.minutes_after = None
            if isinstance(parsed, time):
                rem.time = parsed.strftime("%H:%M")
                rem.interval_hours = None
            else:
                rem.time = None
                rem.interval_hours = int(parsed.total_seconds() // 3600)
        if not commit_session(session):
            logger.error(
                "Failed to commit reminder via webapp for user %s", user_id
            )
            return "error", None, None, None
        session.refresh(rem)
        return "ok", rem, None, None

    status, rem, plan, limit = await run_db(db_save, sessionmaker=SessionLocal)
    if status == "not_found":
        await update.effective_message.reply_text("Не найдено")
        return
    if status == "limit":
        await update.effective_message.reply_text(
            f"У вас уже {limit} активных (лимит {plan.upper()}). "
            "Отключите одно или откройте PRO.",
        )
        return
    if status == "error":
        return

    schedule_reminder(rem, context.job_queue)
    text, keyboard = await run_db(
        _render_reminders, user_id, sessionmaker=SessionLocal
    )
    await update.effective_message.reply_text(
        text, reply_markup=keyboard, parse_mode="HTML"
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
        if not commit_session(session):
            logger.error("Failed to commit reminder deletion for %s", rid)
            if message:
                await message.reply_text("⚠️ Не удалось удалить напоминание.")
            return
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
        if not commit_session(session):
            logger.error(
                "Failed to log reminder trigger for reminder %s", rid
            )
            return
        user = session.get(User, chat_id)
        text = _describe(rem, user)
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
        if not commit_session(session):
            logger.error(
                "Failed to log reminder action %s for reminder %s", action, rid
            )
            return
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

    def db_action(session):
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            return "not_found", None
        if action == "del":
            session.delete(rem)
        elif action == "toggle":
            rem.is_enabled = not rem.is_enabled
        else:
            return "unknown", None
        if not commit_session(session):
            logger.error(
                "Failed to commit reminder action %s for reminder %s", action, rid
            )
            return "error", None
        if action != "del":
            session.refresh(rem)
        return action, rem

    status, rem = await run_db(db_action, sessionmaker=SessionLocal)
    if status == "not_found":
        await query.answer("Не найдено", show_alert=True)
        return
    if status == "unknown":
        await query.answer("Неизвестное действие", show_alert=True)
        return
    if status == "error":
        return

    if status == "toggle":
        if rem and rem.is_enabled:
            schedule_reminder(rem, context.job_queue)
        else:
            for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
                job.schedule_removal()
    else:  # del
        for job in context.job_queue.get_jobs_by_name(f"reminder_{rid}"):
            job.schedule_removal()

    text, keyboard = await run_db(
        _render_reminders, user_id, sessionmaker=SessionLocal
    )
    try:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            await query.answer()
        else:
            raise
    else:
        await query.answer("Готово ✅")



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
    reminder_action_cb, pattern="^rem_(del|toggle):"
)
reminder_webapp_handler = MessageHandler(
    filters.StatusUpdate.WEB_APP_DATA, reminder_webapp_save
)
