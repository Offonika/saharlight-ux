"""Handlers for personal reminders."""

from __future__ import annotations

import datetime
import json
import logging
import re
from datetime import time, timedelta, timezone
from typing import Awaitable, Callable, Literal, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import parse_qsl

from sqlalchemy.orm import Session, sessionmaker
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest, TelegramError

from services.api.app import config
from services.api.app.diabetes.services.db import (
    Reminder,
    ReminderLog,
    SessionLocal as _SessionLocal,
    User,
)
from services.api.app.diabetes.services.repository import CommitError, commit as _commit
from services.api.app.diabetes.utils.helpers import (
    INVALID_TIME_MSG,
    parse_time_interval,
)
from . import UserData

run_db: Callable[..., Awaitable[object]] | None
try:
    from services.api.app.diabetes.services.db import run_db as _run_db
except ImportError:  # pragma: no cover - optional db runner
    logging.getLogger(__name__).info(
        "run_db is unavailable; proceeding without async DB runner"
    )
    run_db = None
else:
    run_db = cast(Callable[..., Awaitable[object]], _run_db)

logger = logging.getLogger(__name__)

SessionLocal: sessionmaker[Session] = _SessionLocal
commit: Callable[[Session], None] = _commit

DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]

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
    tz: datetime.tzinfo = timezone.utc
    tzname = getattr(user, "timezone", None)
    if tzname:
        try:
            tz = ZoneInfo(tzname)
        except ZoneInfoNotFoundError:
            logger.warning(
                "Invalid timezone for user %s: %s",
                getattr(user, "telegram_id", None),
                tzname,
            )
        except (OSError, ValueError) as exc:
            logger.exception("Unexpected error loading timezone %s: %s", tzname, exc)
    try:
        now = dt_cls.now(tz)
    except TypeError:
        now = dt_cls.now().replace(tzinfo=tz)
    next_dt: datetime.datetime | None
    if rem.time:
        type_icon = "⏰"
        next_dt = now.replace(
            hour=rem.time.hour, minute=rem.time.minute, second=0, microsecond=0
        )
        if next_dt <= now:
            next_dt += timedelta(days=1)
        base = rem.time.strftime("%H:%M")
    elif rem.interval_hours:
        type_icon = "⏱"
        next_dt = now + timedelta(hours=rem.interval_hours)
        base = f"каждые {rem.interval_hours} ч"
    elif rem.minutes_after is not None:
        type_icon = "📸"
        next_dt = now + timedelta(minutes=float(rem.minutes_after))
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
    session: Session, user_id: int
) -> tuple[str, InlineKeyboardMarkup | None]:
    rems = session.query(Reminder).filter_by(telegram_id=user_id).all()
    user = session.query(User).filter_by(telegram_id=user_id).first()
    limit = _limit_for(user)
    active_count = sum(1 for r in rems if r.is_enabled)
    header = f"Ваши напоминания  ({active_count} / {limit} 🔔)"
    if active_count > limit:
        header += " ⚠️"

    webapp_enabled = bool(config.settings.public_origin)
    add_button_row = None
    if webapp_enabled:
        add_button_row = [
            InlineKeyboardButton(
                "➕ Добавить",
                web_app=WebAppInfo(config.build_ui_url("/reminders/new")),
            )
        ]
    if not rems:
        text = header

        if webapp_enabled and add_button_row is not None:
            text += "\nУ вас нет напоминаний. Нажмите кнопку ниже или отправьте /addreminder."
            return text, InlineKeyboardMarkup([add_button_row])
        text += "\nУ вас нет напоминаний. Отправьте /addreminder."
        return text, None

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
        if webapp_enabled:
            row.append(
                InlineKeyboardButton(
                    "✏️",
                    web_app=WebAppInfo(
                        config.build_ui_url(f"/reminders?id={r.id}")
                    ),
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

    def extend(
        section: str, items: list[tuple[str, list[InlineKeyboardButton]]]
    ) -> None:
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

    if add_button_row is not None:
        buttons.append(add_button_row)
    text = header + "\n" + "\n".join(lines)
    return text, InlineKeyboardMarkup(buttons)


def schedule_reminder(rem: Reminder, job_queue: DefaultJobQueue | None) -> None:
    if job_queue is None:
        logger.warning("schedule_reminder called without job_queue")
        return
    name = f"reminder_{rem.id}"
    for job in job_queue.get_jobs_by_name(name):
        job.schedule_removal()
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

    tz: datetime.tzinfo = timezone.utc
    user = rem.__dict__.get("user")
    if user is None or getattr(user, "timezone", None) is None:
        with SessionLocal() as session:
            user = session.get(User, rem.telegram_id)
    tzname = getattr(user, "timezone", None) if user else None
    if tzname:
        try:
            tz = ZoneInfo(tzname)
        except ZoneInfoNotFoundError:
            logger.warning(
                "Invalid timezone for user %s: %s",
                getattr(user, "telegram_id", None),
                tzname,
            )
        except (OSError, ValueError) as exc:
            logger.exception("Unexpected error loading timezone %s: %s", tzname, exc)

    if rem.type in {"sugar", "long_insulin", "medicine"}:
        if rem.time:
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
                time=rem.time.replace(tzinfo=tz),
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


def schedule_all(job_queue: DefaultJobQueue | None) -> None:
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
    """Reply with the user's reminders list."""

    user = update.effective_user
    message: Message | None = update.message
    if user is None or message is None:
        return
    user_id = user.id

    render_fn = cast(
        Callable[[Session, int], tuple[str, InlineKeyboardMarkup | None]],
        _render_reminders,
    )
    if run_db is None:
        with SessionLocal() as session:
            text, keyboard = render_fn(session, user_id)
    else:
        text, keyboard = cast(
            tuple[str, InlineKeyboardMarkup | None],
            await run_db(render_fn, user_id, sessionmaker=SessionLocal),
        )

    if keyboard is not None:
        await message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.reply_text(text, parse_mode="HTML")


async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a reminder using command arguments."""
    user = update.effective_user
    message: Message | None = update.message
    if user is None or message is None:
        return
    user_id = user.id
    args = getattr(context, "args", [])
    if len(args) < 2:
        await message.reply_text(
            "Использование: /addreminder <type> <value>"  # noqa: RUF001
        )
        return
    rtype, value = args[0], args[1]
    if rtype not in REMINDER_NAMES:
        await message.reply_text("Неизвестный тип напоминания.")
        return
    reminder = Reminder(telegram_id=user_id, type=rtype)
    if rtype == "sugar":
        if ":" in value:
            try:
                parsed = parse_time_interval(value)
            except ValueError:
                await message.reply_text(INVALID_TIME_MSG)
                return
            if isinstance(parsed, time):
                reminder.time = parsed.strftime("%H:%M")
            else:
                await message.reply_text(INVALID_TIME_MSG)
                return
        else:
            try:
                reminder.interval_hours = int(value)
            except ValueError:
                await message.reply_text("Интервал должен быть числом.")
                return
    elif rtype in {"long_insulin", "medicine"}:
        try:
            parsed = parse_time_interval(value)
        except ValueError:
            await message.reply_text(INVALID_TIME_MSG)
            return
        if isinstance(parsed, time):
            reminder.time = parsed.strftime("%H:%M")
        else:
            await message.reply_text(INVALID_TIME_MSG)
            return
    elif rtype == "xe_after":
        try:
            reminder.minutes_after = int(value)
        except ValueError:
            await message.reply_text("Значение должно быть числом.")
            return

    def db_add(session: Session) -> tuple[str, User | None, int, int]:
        count = session.query(Reminder).filter_by(telegram_id=user_id).count()
        db_user = session.get(User, user_id)
        limit = _limit_for(db_user)
        if count >= limit:
            return "limit", db_user, limit, count
        session.add(reminder)
        try:
            commit(session)
        except CommitError:
            logger.error("Failed to commit new reminder for user %s", user_id)
            return "error", db_user, limit, count
        return "ok", db_user, limit, reminder.id

    if run_db is None:
        with SessionLocal() as session:
            status, db_user, limit, rid_or_count = db_add(session)
    else:
        status, db_user, limit, rid_or_count = await run_db(
            db_add, sessionmaker=SessionLocal
        )

    if status == "limit":
        count = rid_or_count
        await message.reply_text(
            (
                f"У вас уже {count} активных из {limit}. Отключите одно или Апгрейд до Pro, чтобы поднять лимит до 10"
            ),
        )
        return
    if status == "error":
        await message.reply_text("⚠️ Не удалось сохранить напоминание.")
        return

    rid = rid_or_count
    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
    if job_queue is not None:
        for job in job_queue.get_jobs_by_name(f"reminder_{rid}"):
            job.schedule_removal()
        schedule_reminder(reminder, job_queue)
    await message.reply_text(f"Сохранено: {_describe(reminder, db_user)}")


async def reminder_webapp_save(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Save reminder data sent from the web app."""
    msg: Message | None = update.effective_message
    user = update.effective_user
    if msg is None or user is None:
        return
    web_app = getattr(msg, "web_app_data", None)
    if web_app is None:
        return
    raw = web_app.data
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = dict(parse_qsl(raw))

    snooze_raw = data.get("snooze")
    if snooze_raw is not None:
        rid = data.get("id")
        if rid is None:
            return
        try:
            minutes = int(snooze_raw)
        except (TypeError, ValueError):
            await msg.reply_text("Неверный формат")
            return
        user_id = user.id

        def log_snooze(session: Session) -> Literal["ok"] | Literal["error"]:
            session.add(
                ReminderLog(reminder_id=int(rid), telegram_id=user_id, action="snooze")
            )
            try:
                commit(session)
            except CommitError:
                logger.error("Failed to log reminder snooze for reminder %s", rid)
                return "error"
            return "ok"

        if run_db is None:
            with SessionLocal() as session:
                status = log_snooze(session)
        else:
            status = cast(
                Literal["ok"] | Literal["error"],
                await run_db(log_snooze, sessionmaker=SessionLocal),
            )
        if status == "ok":
            job_queue: DefaultJobQueue | None = cast(
                DefaultJobQueue | None, context.job_queue
            )
            if job_queue is not None:
                job_queue.run_once(
                    reminder_job,
                    when=timedelta(minutes=minutes),
                    data={"reminder_id": int(rid), "chat_id": user_id},
                    name=f"reminder_{rid}",
                )
            await msg.reply_text(f"⏰ Отложено на {minutes} минут")
        return

    rtype = data.get("type")
    raw_value = data.get("value")
    rid = data.get("id")
    if not rtype or raw_value is None:
        return
    if rtype not in REMINDER_NAMES:
        await msg.reply_text("Неизвестный тип напоминания.")
        return
    value = str(raw_value).strip()
    if not value:
        return
    logger.debug("Received raw reminder value: %r", value)
    user_id = user.id
    if rtype == "xe_after":
        try:
            minutes = int(value)
        except ValueError:
            await msg.reply_text("Неверный формат")
            return
        parsed = None
    else:
        if not re.fullmatch(r"\d{1,2}:\d{2}|\d+h", value):
            logger.warning("Invalid reminder value format: %s", value)
            await msg.reply_text(
                "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h."
            )
            return
        try:
            parsed = parse_time_interval(value)
        except ValueError:
            logger.warning("Failed to parse reminder value: %s", value)
            await msg.reply_text(
                "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h."
            )
            return
        minutes = None

    def db_save(
        session: Session,
    ) -> (
        tuple[Literal["not_found"], None, None, None]
        | tuple[Literal["limit"], None, str, int]
        | tuple[Literal["error"], None, None, None]
        | tuple[Literal["ok"], Reminder, None, None]
    ):
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
                rem.time = parsed
                rem.interval_hours = None
            else:
                rem.time = None
                if parsed is None:
                    return "error", None, None, None
                rem.interval_hours = int(parsed.total_seconds() // 3600)
        try:
            commit(session)
        except CommitError:
            logger.error("Failed to commit reminder via webapp for user %s", user_id)
            return "error", None, None, None
        session.refresh(rem)
        return "ok", rem, None, None

    if run_db is None:
        with SessionLocal() as session:
            status, rem, plan, limit = db_save(session)
    else:
        status, rem, plan, limit = await run_db(db_save, sessionmaker=SessionLocal)
    if status == "not_found":
        await msg.reply_text("Не найдено")
        return
    if status == "limit":
        if plan is None:
            return
        await msg.reply_text(
            (
                f"У вас уже {limit} активных (лимит {plan.upper()}). Отключите одно или откройте PRO."
            ),
        )
        return
    if status == "error":
        await msg.reply_text("⚠️ Не удалось сохранить напоминание.")
        return

    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
    if job_queue is not None and rem is not None:
        schedule_reminder(rem, job_queue)
    render_fn = cast(
        Callable[[object], tuple[str, InlineKeyboardMarkup | None]],
        _render_reminders,
    )
    if run_db is None:
        with SessionLocal() as session:
            text, keyboard = render_fn(session, user_id)
    else:
        text, keyboard = await run_db(render_fn, user_id, sessionmaker=SessionLocal)
    if keyboard is not None:
        await msg.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await msg.reply_text(text, parse_mode="HTML")


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message: Message | None = update.message or (
        update.callback_query.message if update.callback_query else None
    )
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
        try:
            commit(session)
        except CommitError:
            logger.error("Failed to commit reminder deletion for %s", rid)
            if message:
                await message.reply_text("⚠️ Не удалось удалить напоминание.")
            return
    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
    if job_queue is not None:
        for job in job_queue.get_jobs_by_name(f"reminder_{rid}"):
            job.schedule_removal()
    if message:
        await message.reply_text("Удалено")


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    if job is None or job.data is None:
        return
    data = cast(UserData, job.data)
    rid = data.get("reminder_id")
    chat_id = data.get("chat_id")
    if rid is None or chat_id is None:
        return
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem:
            return
        session.add(ReminderLog(reminder_id=rid, telegram_id=chat_id, action="trigger"))
        try:
            commit(session)
        except CommitError:
            logger.error("Failed to log reminder trigger for reminder %s", rid)
            return
        user = session.get(User, chat_id)
        text = _describe(rem, user)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Отложить 10 мин", callback_data=f"remind_snooze:{rid}:10"
                ),
                InlineKeyboardButton("Отмена", callback_data=f"remind_cancel:{rid}"),
            ]
        ]
    )
    try:
        await context.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=keyboard
        )
    except TelegramError:
        logger.exception("Failed to send reminder %s to chat %s", rid, chat_id)


async def reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or query.data is None or user is None:
        return
    parts = query.data.split(":")
    if len(parts) < 2:
        return
    action, rid_str = parts[0], parts[1]

    try:
        rid = int(rid_str)
    except ValueError:
        return
    minutes: int | None = None
    if len(parts) > 2:
        try:
            minutes = int(parts[2])
        except ValueError:
            minutes = None

    chat_id = user.id
    snooze_minutes: int | None = None
    with SessionLocal() as session:
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != chat_id:
            await query.answer("Не найдено", show_alert=True)
            return
        await query.answer()

        if action == "remind_snooze":
            snooze_minutes = minutes or 10
        log_action = action
        session.add(
            ReminderLog(
                reminder_id=rid,
                telegram_id=chat_id,
                action=log_action,
                snooze_minutes=snooze_minutes,
            )
        )
        try:
            commit(session)
        except CommitError:
            logger.error(
                "Failed to log reminder action %s for reminder %s", log_action, rid
            )
            return

    if action == "remind_snooze":
        mins = minutes or 10
        job_queue: DefaultJobQueue | None = cast(
            DefaultJobQueue | None, context.job_queue
        )
        if job_queue is not None:
            job_queue.run_once(
                reminder_job,
                when=timedelta(minutes=mins),
                data={"reminder_id": rid, "chat_id": chat_id},
                name=f"reminder_{rid}",
            )
        try:

            await query.edit_message_text(f"⏰ Отложено на {mins} минут")

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


async def reminder_action_cb(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or query.data is None or user is None:
        return
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
    user_id = user.id

    def db_action(
        session: Session,
    ) -> (
        tuple[Literal["not_found"], None]
        | tuple[Literal["unknown"], None]
        | tuple[Literal["error"], None]
        | tuple[Literal["del"], None]
        | tuple[Literal["toggle"], Reminder]
    ):
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            return "not_found", None
        if action == "del":
            session.delete(rem)  # type: ignore[no-untyped-call]
        elif action == "toggle":
            rem.is_enabled = not rem.is_enabled
        else:
            return "unknown", None
        try:
            commit(session)
        except CommitError:
            logger.error(
                "Failed to commit reminder action %s for reminder %s", action, rid
            )
            return "error", None
        if action == "toggle":
            session.refresh(rem)
            return "toggle", rem
        return "del", None

    if run_db is None:
        with SessionLocal() as session:
            status, rem = db_action(session)
    else:
        status, rem = cast(
            tuple[str, Reminder | None],
            await run_db(db_action, sessionmaker=SessionLocal),
        )
    if status == "not_found":
        await query.answer("Не найдено", show_alert=True)
        return
    if status == "unknown":
        await query.answer("Неизвестное действие", show_alert=True)
        return
    if status == "error":
        return

    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
    if status == "toggle":
        if rem and rem.is_enabled:
            schedule_reminder(rem, job_queue)
        elif job_queue is not None:
            for job in job_queue.get_jobs_by_name(f"reminder_{rid}"):
                job.schedule_removal()
    else:  # del
        if job_queue is not None:
            for job in job_queue.get_jobs_by_name(f"reminder_{rid}"):
                job.schedule_removal()

    render_fn = cast(
        Callable[[Session, int], tuple[str, InlineKeyboardMarkup | None]],
        _render_reminders,
    )
    if run_db is None:
        with SessionLocal() as session:
            text, keyboard = render_fn(session, user_id)
    else:
        text, keyboard = cast(
            tuple[str, InlineKeyboardMarkup | None],
            await run_db(render_fn, user_id, sessionmaker=SessionLocal),
        )
    try:
        if keyboard is not None:
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=keyboard
            )
        else:
            await query.edit_message_text(text, parse_mode="HTML")
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            await query.answer()
        else:
            raise
    else:
        await query.answer("Готово ✅")


def schedule_after_meal(user_id: int, job_queue: DefaultJobQueue | None) -> None:
    if job_queue is None:
        logger.warning("schedule_after_meal called without job_queue")
        return
    with SessionLocal() as session:
        rems = (
            session.query(Reminder)
            .filter_by(telegram_id=user_id, type="xe_after", is_enabled=True)
            .all()
        )
    for rem in rems:
        minutes_after = rem.minutes_after
        if minutes_after is None:
            continue
        job_queue.run_once(
            reminder_job,
            when=timedelta(minutes=float(minutes_after)),
            data={"reminder_id": rem.id, "chat_id": user_id},
            name=f"reminder_{rem.id}",
        )


reminder_action_handler = CallbackQueryHandler(
    reminder_action_cb, pattern="^rem_(del|toggle):"
)
reminder_webapp_handler = MessageHandler(
    filters.StatusUpdate.WEB_APP_DATA, reminder_webapp_save
)


__all__ = [
    "schedule_reminder",
    "schedule_all",
    "reminders_list",
    "add_reminder",
    "reminder_webapp_save",
    "delete_reminder",
    "reminder_job",
    "reminder_callback",
    "reminder_action_cb",
    "schedule_after_meal",
    "reminder_action_handler",
    "reminder_webapp_handler",
    "SessionLocal",
    "commit",
]
