"""Handlers for personal reminders."""

from __future__ import annotations

import datetime
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from datetime import time, timedelta, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Literal, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import parse_qsl

import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker, selectinload
from sqlalchemy.orm.exc import DetachedInstanceError
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
    MessageHandler,
    filters,
)
from telegram.error import BadRequest, TelegramError

from services.api.app import config, reminder_events
from services.api.app.diabetes.services.db import (
    Entry,
    Reminder,
    ReminderLog,
    SessionLocal as _SessionLocal,
    SubscriptionPlan,
    User,
    Profile,
)
from services.api.app.diabetes.services.repository import CommitError, commit as _commit
from services.api.app.diabetes.utils.helpers import (
    INVALID_TIME_MSG,
    parse_time_interval,
)
from services.api.app.diabetes.utils.jobs import _remove_jobs, schedule_once
from services.api.app.diabetes.utils.ui import menu_keyboard
from services.api.app.diabetes.schemas.reminders import ScheduleKind
from .reminder_jobs import DefaultJobQueue, schedule_reminder
from .alert_handlers import check_alert as _check_alert

check_alert = _check_alert

if TYPE_CHECKING:
    from . import UserData

run_db: Callable[..., Awaitable[Any]] | None
try:
    from services.api.app.diabetes.services.db import run_db as _run_db
except ImportError:  # pragma: no cover - optional db runner
    logging.getLogger(__name__).info("run_db is unavailable; proceeding without async DB runner")
    run_db = None
else:
    run_db = cast(Callable[..., Awaitable[Any]], _run_db)

logger = logging.getLogger(__name__)

SessionLocal: sessionmaker[Session] = _SessionLocal
commit: Callable[[Session], None] = _commit


class DbActionStatus(Enum):
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"
    ERROR = "error"
    DELETE = "del"
    TOGGLE = "toggle"


@dataclass
class DbActionResult:
    status: DbActionStatus
    reminder: Reminder | None = None


PLAN_LIMITS = {
    SubscriptionPlan.FREE: 5,
    SubscriptionPlan.PRO: 10,
}


# Map reminder type codes to display names
REMINDER_NAMES = {
    "sugar": "Сахар",  # noqa: RUF001
    "insulin_short": "Короткий инсулин",  # noqa: RUF001
    "insulin_long": "Длинный инсулин",  # noqa: RUF001
    "after_meal": "Проверить ХЕ после еды",  # noqa: RUF001
    "meal": "Приём пищи",  # noqa: RUF001
    "sensor_change": "Смена сенсора",  # noqa: RUF001
    "injection_site": "Смена места инъекции",  # noqa: RUF001
    "custom": "Другое",  # noqa: RUF001
}

REMINDER_ACTIONS = {
    "sugar": "Замерить сахар",  # noqa: RUF001
    "insulin_short": "Короткий инсулин",  # noqa: RUF001
    "insulin_long": "Длинный инсулин",  # noqa: RUF001
    "after_meal": "Проверить ХЕ",  # noqa: RUF001
    "meal": "Приём пищи",  # noqa: RUF001
    "sensor_change": "Сменить сенсор",  # noqa: RUF001
    "injection_site": "Сменить место инъекции",  # noqa: RUF001
    "custom": "Напоминание",  # noqa: RUF001
}


def _limit_for(user: User | None) -> int:
    plan = getattr(user, "plan", SubscriptionPlan.FREE)
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[SubscriptionPlan.FREE])


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
        user = cast(User | None, getattr(rem, "user", None))
    tz: datetime.tzinfo = timezone.utc
    profile = None
    if user is not None:
        try:
            profile = getattr(user, "profile")
        except DetachedInstanceError:
            profile = None
    tzname = getattr(profile, "timezone", None)
    if tzname is None and user is not None:
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
        next_dt = now.replace(hour=rem.time.hour, minute=rem.time.minute, second=0, microsecond=0)
        if next_dt <= now:
            next_dt += timedelta(days=1)
        base = rem.time.strftime("%H:%M")
    elif rem.interval_hours or rem.interval_minutes:
        type_icon = "⏱"
        minutes = rem.interval_hours * 60 if rem.interval_hours is not None else rem.interval_minutes or 0
        next_dt = now + timedelta(minutes=minutes)
        if rem.interval_hours:
            base = f"каждые {rem.interval_hours} ч"
        else:
            base = f"каждые {rem.interval_minutes} мин"
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


def _render_reminders(session: Session, user_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    settings = config.get_settings()
    rems = session.query(Reminder).filter_by(telegram_id=user_id).all()
    user = session.query(User).filter_by(telegram_id=user_id).first()
    limit = _limit_for(user)
    active_count = sum(1 for r in rems if r.is_enabled)
    header = f"Ваши напоминания ({active_count} / {limit} 🔔)"
    if active_count > limit:
        header += " ⚠️"

    webapp_enabled: bool = bool(settings.public_origin)

    origin = (settings.public_origin or "").rstrip("/")
    base_url = (getattr(settings, "ui_base_url", "") or "").strip("/")

    def build_url(path: str) -> str:
        rel = path.lstrip("/")
        return f"{origin}/{base_url}/{rel}" if base_url else f"{origin}/{rel}"

    add_button = (
        InlineKeyboardButton(
            "➕ Добавить",
            web_app=WebAppInfo(build_url("/reminders/new")),
        )
        if webapp_enabled
        else InlineKeyboardButton("➕ Добавить", callback_data="rem_add")
    )
    add_button_row = [add_button]
    if not rems:
        text = header + "\nУ вас нет напоминаний. Нажмите кнопку ниже или отправьте /addreminder."
        return text, InlineKeyboardMarkup([add_button_row])

    by_time: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_interval: list[tuple[str, list[InlineKeyboardButton]]] = []
    by_photo: list[tuple[str, list[InlineKeyboardButton]]] = []

    for r in rems:
        title = _describe(r, user)
        if not r.is_enabled:
            title = f"<s>{title}</s>"
        line = f"{r.id}. {title}"
        status_icon = "🔔" if r.is_enabled else "🔕"
        edit_button = (
            InlineKeyboardButton(
                "✏️",
                web_app=WebAppInfo(build_url(f"/reminders?id={r.id}")),
            )
            if webapp_enabled
            else InlineKeyboardButton("✏️", callback_data=f"rem_edit:{r.id}")
        )
        row: list[InlineKeyboardButton] = [edit_button]
        row.extend(
            [
                InlineKeyboardButton("🗑️", callback_data=f"rem_del:{r.id}"),
                InlineKeyboardButton(status_icon, callback_data=f"rem_toggle:{r.id}"),
            ]
        )
        if r.time:
            by_time.append((line, row))
        elif r.interval_hours or r.interval_minutes:
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

    buttons.append(add_button_row)
    text = header + "\n" + "\n".join(lines)
    return text, InlineKeyboardMarkup(buttons)


def _reschedule_job(job_queue: DefaultJobQueue, reminder: Reminder, user: User) -> None:
    """Пересоздаёт задачу с обновлённым временем."""
    base = f"reminder_{reminder.id}"
    removed = _remove_jobs(job_queue, base)
    logger.info("🗑 removed %d jobs for %s", removed, base)

    schedule_reminder(reminder, job_queue, user)
    next_run: datetime.datetime | None = None
    scheduler = getattr(job_queue, "scheduler", None)
    job = (
        scheduler.get_job(job_id=base)  # type: ignore[attr-defined]
        if getattr(scheduler, "get_job", None) is not None
        else None
    )
    if job is not None:
        next_run = (
            getattr(job, "next_run_time", None)
            or getattr(job, "next_t", None)
            or getattr(job, "when", None)
            or getattr(job, "run_time", None)
        )
    logger.info("♻️ rescheduled %s -> next_run=%s", base, next_run)


def schedule_all(job_queue: DefaultJobQueue | None) -> None:
    if job_queue is None:
        logger.warning("schedule_all called without job_queue")
        return
    with SessionLocal() as session:
        reminders = session.query(Reminder).options(selectinload(Reminder.user).joinedload(User.profile)).all()
        count = len(reminders)
        logger.debug("Found %d reminders to schedule", count)
        for rem in reminders:
            base = f"reminder_{rem.id}"
            removed = _remove_jobs(job_queue, base)
            logger.info("🗑 removed %d jobs named %s", removed, base)
            schedule_reminder(rem, job_queue, rem.user)
            job = next(iter(job_queue.get_jobs_by_name(base)), None)
            next_run = (
                getattr(job, "next_run_time", None)
                or getattr(job, "next_t", None)
                or getattr(job, "when", None)
                or getattr(job, "run_time", None)
                if job is not None
                else None
            )
            logger.info("⏰ Scheduled job %s -> next_run=%s", base, next_run)

        # 🔎 Отладка: просто логируем список активных джобов
        jobs = job_queue.jobs()
        logger.info("📋 Total scheduled jobs: %d", len(jobs))
        for job in jobs:
            logger.info(
                "📅 Scheduled job: name=%s data=%s",
                getattr(job, "name", None),
                getattr(job, "data", None),
            )

        logger.debug("Scheduled %d reminders", count)


async def create_reminder_from_preset(user_id: int, code: str, job_queue: DefaultJobQueue | None) -> Reminder | None:
    """Create and schedule a reminder based on a preset code."""

    presets: dict[str, dict[str, object]] = {
        "sugar_08": {"type": "sugar", "time": time(8, 0)},
        "long_22": {"type": "insulin_long", "time": time(22, 0)},
        "pills_09": {
            "type": "custom",
            "title": "Таблетки",  # noqa: RUF001
            "time": time(9, 0),
        },
    }
    preset = presets.get(code)
    if preset is None:
        logger.warning("Unknown reminder preset: %s", code)
        return None

    reminder = Reminder(telegram_id=user_id, type=cast(str, preset["type"]))
    reminder.time = cast(time, preset["time"])
    reminder.kind = ScheduleKind.at_time.value
    title = preset.get("title")
    if title is not None:
        reminder.title = cast(str, title)

    def db_save(session: Session) -> tuple[Reminder | None, User | None]:
        user = session.get(User, user_id)
        exists = (
            session.query(Reminder)
            .filter_by(
                telegram_id=user_id,
                type=reminder.type,
                time=reminder.time,
            )
            .first()
        )
        if exists is not None:
            return None, user
        session.add(reminder)
        try:
            commit(session)
            session.refresh(reminder)
        except CommitError:
            logger.exception("Failed to commit preset reminder for user %s", user_id)
            return None, user
        if user is not None:
            reminder.user = user
        return reminder, user

    if run_db is None:
        with SessionLocal() as session:
            saved, db_user = db_save(session)
    else:
        saved, db_user = await run_db(db_save, sessionmaker=SessionLocal)

    if saved is None:
        logger.info("Preset reminder %s not created for user %s", code, user_id)
        return None

    logger.info(
        "Created preset reminder %s for user %s: id=%s",
        code,
        user_id,
        saved.id,
    )
    if job_queue is not None and db_user is not None:
        user_to_schedule = db_user
        if sqlalchemy.inspect(db_user).detached:
            user_to_schedule = None
        schedule_reminder(saved, job_queue, user_to_schedule)
        logger.info("Scheduled preset reminder %s", saved.id)
    else:
        await reminder_events.notify_reminder_saved(saved.id)
        logger.info("Sent reminder_saved event for %s", saved.id)
    return saved


async def reminders_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    show_menu: bool = True,
) -> None:
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
    try:
        if run_db is None:
            with SessionLocal() as session:
                text, keyboard = render_fn(session, user_id)
        else:
            text, keyboard = cast(
                tuple[str, InlineKeyboardMarkup | None],
                await run_db(render_fn, user_id, sessionmaker=SessionLocal),
            )
    except SQLAlchemyError:
        logger.exception("Failed to render reminders")
        await message.reply_text("Не удалось получить напоминания, попробуйте позже.")
        return

    if show_menu:
        await message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard())

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
    if not args:
        await message.reply_text(
            "Использование: /addreminder <type> <value>"  # noqa: RUF001
        )
        return
    rtype = args[0]
    value = args[1] if len(args) > 1 else None
    if rtype == "after_meal" and value is None:

        def load_default(session: Session) -> int | None:
            settings = session.get(Profile, user_id)
            return getattr(settings, "postmeal_check_min", None)

        if run_db is None:
            with SessionLocal() as session:
                default_minutes = load_default(session)
        else:
            default_minutes = await run_db(load_default, sessionmaker=SessionLocal)
        if default_minutes is None:
            await message.reply_text(
                "Использование: /addreminder <type> <value>"  # noqa: RUF001
            )
            return
        value = str(default_minutes)
    elif value is None:
        await message.reply_text(
            "Использование: /addreminder <type> <value>"  # noqa: RUF001
        )
        return
    assert value is not None
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
                reminder.time = parsed
                reminder.kind = ScheduleKind.at_time.value
            else:
                await message.reply_text(INVALID_TIME_MSG)
                return
        else:
            try:
                hours = int(value)
            except ValueError:
                await message.reply_text("Интервал должен быть числом.")
                return
            reminder.interval_hours = hours
            reminder.interval_minutes = hours * 60
            reminder.kind = ScheduleKind.every.value
    elif rtype in {
        "insulin_short",
        "insulin_long",
        "meal",
        "sensor_change",
        "injection_site",
        "custom",
    }:
        try:
            parsed = parse_time_interval(value)
        except ValueError:
            await message.reply_text(INVALID_TIME_MSG)
            return
        if isinstance(parsed, time):
            reminder.time = parsed
            reminder.kind = ScheduleKind.at_time.value
        else:
            await message.reply_text(INVALID_TIME_MSG)
            return
    elif rtype == "after_meal":
        try:
            reminder.minutes_after = int(value)
        except ValueError:
            await message.reply_text("Значение должно быть числом.")
            return
        reminder.kind = ScheduleKind.after_event.value

    def db_add(session: Session) -> tuple[str, User | None, int, int]:
        count = session.query(Reminder).filter_by(telegram_id=user_id, is_enabled=True).count()
        db_user = session.get(User, user_id)
        limit = _limit_for(db_user)
        if count >= limit:
            return "limit", db_user, limit, count
        session.add(reminder)
        logger.debug(
            "Saving reminder for user %s: type=%s kind=%s time=%s interval_hours=%s interval_minutes=%s minutes_after=%s",
            user_id,
            reminder.type,
            reminder.kind,
            reminder.time,
            reminder.interval_hours,
            reminder.interval_minutes,
            reminder.minutes_after,
        )
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
        status, db_user, limit, rid_or_count = await run_db(db_add, sessionmaker=SessionLocal)

    if status == "limit":
        count = rid_or_count
        await message.reply_text(
            (f"У вас уже {count} активных из {limit}. Отключите одно или Апгрейд до Pro, чтобы поднять лимит до 10"),
        )
        return
    if status == "error":
        await message.reply_text("⚠️ Не удалось сохранить напоминание.")
        return
    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
    if job_queue is not None and db_user is not None:
        schedule_reminder(reminder, job_queue, db_user)
        logger.debug(
            "Job queue present; suppressed reminder_saved event for %s",
            reminder.id,
        )
    else:
        await reminder_events.notify_reminder_saved(reminder.id)
        logger.debug("Sent reminder_saved event for %s", reminder.id)
    await message.reply_text(f"Сохранено: {_describe(reminder, db_user)}")


async def reminder_webapp_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    sugar_raw = data.get("sugar")
    if sugar_raw is not None:
        rid = data.get("id")
        if rid is None:
            return
        try:
            sugar_val = float(sugar_raw)
        except (TypeError, ValueError):
            await msg.reply_text("Неверный формат")
            return
        user_id = user.id

        def save_sugar(session: Session) -> Literal["ok"] | Literal["error"]:
            session.add(
                Entry(
                    telegram_id=user_id,
                    event_time=datetime.datetime.now(datetime.timezone.utc),
                    sugar_before=sugar_val,
                )
            )
            session.add(
                ReminderLog(
                    reminder_id=int(rid),
                    telegram_id=user_id,
                    action="value_saved",
                )
            )
            try:
                commit(session)
            except CommitError:
                logger.error("Failed to save sugar value for reminder %s", rid)
                return "error"
            return "ok"

        if run_db is None:
            with SessionLocal() as session:
                status = save_sugar(session)
        else:
            status = cast(
                Literal["ok"] | Literal["error"],
                await run_db(save_sugar, sessionmaker=SessionLocal),
            )
        if status == "ok":
            await msg.reply_text(f"Записано {sugar_val} ммоль/л")
            await check_alert(update, context, sugar_val)
        return

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
            session.add(ReminderLog(reminder_id=int(rid), telegram_id=user_id, action="snooze"))
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
            job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
            if job_queue is not None:
                schedule_once(
                    job_queue,
                    reminder_job,
                    when=timedelta(minutes=minutes),
                    data={"reminder_id": int(rid), "chat_id": user_id},
                    name=f"reminder_{rid}_snooze",
                    job_kwargs={
                        "id": f"reminder_{rid}_snooze",
                        "name": f"reminder_{rid}_snooze",
                        "replace_existing": True,
                    },
                )
            await msg.reply_text(f"⏰ Отложено на {minutes} минут")
        return

    rtype = data.get("type")
    rid = data.get("id")
    kind_raw = data.get("kind")
    time_raw = data.get("time")
    interval_minutes_raw = data.get("intervalMinutes")
    minutes_after_raw = data.get("minutesAfter")
    legacy_value = data.get("value")

    if not rtype:
        return
    if rtype not in REMINDER_NAMES:
        await msg.reply_text("Неизвестный тип напоминания.")
        return

    user_id = user.id
    if rtype == "after_meal" and minutes_after_raw is None:

        def load_default(session: Session) -> int | None:
            settings = session.get(Profile, user_id)
            return getattr(settings, "postmeal_check_min", None)

        if run_db is None:
            with SessionLocal() as session:
                default_minutes = load_default(session)
        else:
            default_minutes = await run_db(load_default, sessionmaker=SessionLocal)
        if default_minutes is not None:
            minutes_after_raw = default_minutes

    provided_fields = [
        time_raw is not None,
        interval_minutes_raw is not None,
        minutes_after_raw is not None,
    ]

    minutes: int | None = None
    parsed_time: time | None = None
    interval_minutes: int | None = None

    kind: ScheduleKind | None
    if legacy_value is not None and not any(provided_fields):
        value = str(legacy_value).strip()
        if not value:
            return
        logger.debug("Received raw reminder value: %r", value)
        if rtype == "after_meal":
            try:
                minutes = int(value)
            except ValueError:
                await msg.reply_text("Неверный формат")
                return
            kind = ScheduleKind.after_event
        else:
            if not re.fullmatch(r"\d{1,2}:\d{2}|\d+h", value):
                logger.warning("Invalid reminder value format: %s", value)
                await msg.reply_text(
                    "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h.",
                )
                return
            try:
                parsed = parse_time_interval(value)
            except ValueError:
                logger.warning("Failed to parse reminder value: %s", value)
                await msg.reply_text(
                    "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h.",
                )
                return
            if isinstance(parsed, time):
                parsed_time = parsed
                kind = ScheduleKind.at_time
            else:
                interval_minutes = int(parsed.total_seconds() // 60)
                kind = ScheduleKind.every
        interval_minutes_raw = interval_minutes
        minutes_after_raw = minutes
        time_raw = parsed_time.strftime("%H:%M") if parsed_time else None
        provided_fields = [
            time_raw is not None,
            interval_minutes_raw is not None,
            minutes_after_raw is not None,
        ]
    else:
        if sum(provided_fields) != 1:
            await msg.reply_text("Неверный формат")
            return
        try:
            kind = ScheduleKind(kind_raw) if kind_raw is not None else None
        except ValueError:
            await msg.reply_text("Неверный формат")
            return

        if kind is None:
            if time_raw is not None:
                kind = ScheduleKind.at_time
            elif interval_minutes_raw is not None:
                kind = ScheduleKind.every
            else:
                kind = ScheduleKind.after_event

        if kind is ScheduleKind.at_time and time_raw is None:
            await msg.reply_text("Неверный формат")
            return
        if kind is ScheduleKind.every and interval_minutes_raw is None:
            await msg.reply_text("Неверный формат")
            return
        if kind is ScheduleKind.after_event and minutes_after_raw is None:
            await msg.reply_text("Неверный формат")
            return

    if time_raw is not None and parsed_time is None:
        try:
            parsed = parse_time_interval(str(time_raw))
        except ValueError:
            logger.warning("Failed to parse reminder value: %s", time_raw)
            await msg.reply_text(
                "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h.",
            )
            return
        if not isinstance(parsed, time):
            await msg.reply_text(
                "❌ Неверный формат. Используйте HH:MM или число часов с суффиксом h.",
            )
            return
        parsed_time = parsed
    elif interval_minutes_raw is not None:
        try:
            interval_minutes = int(interval_minutes_raw)
        except (TypeError, ValueError):
            await msg.reply_text("Неверный формат")
            return
    elif minutes_after_raw is not None:
        try:
            minutes = int(minutes_after_raw)
        except (TypeError, ValueError):
            await msg.reply_text("Неверный формат")
            return

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
            count = session.query(Reminder).filter_by(telegram_id=user_id, is_enabled=True).count()
            user = session.get(User, user_id)
            user_plan = getattr(user, "plan", SubscriptionPlan.FREE)
            limit = PLAN_LIMITS.get(user_plan, PLAN_LIMITS[SubscriptionPlan.FREE])
            if count >= limit:
                return "limit", None, user_plan.value, limit
            rem = Reminder(telegram_id=user_id, type=rtype, is_enabled=True)
            session.add(rem)

        rem.kind = kind.value

        if kind is ScheduleKind.after_event:
            rem.minutes_after = minutes
            rem.time = None
            rem.interval_hours = None
            rem.interval_minutes = None
        elif kind is ScheduleKind.every:
            rem.minutes_after = None
            rem.time = None
            rem.interval_minutes = interval_minutes
            rem.interval_hours = (
                interval_minutes // 60 if interval_minutes is not None and interval_minutes % 60 == 0 else None
            )
        else:  # at_time
            rem.minutes_after = None
            rem.interval_hours = None
            rem.interval_minutes = None
            rem.time = parsed_time
        logger.debug(
            "Saving reminder via webapp for user %s: type=%s kind=%s time=%s interval_hours=%s interval_minutes=%s minutes_after=%s",
            user_id,
            rem.type,
            rem.kind,
            rem.time,
            rem.interval_hours,
            rem.interval_minutes,
            rem.minutes_after,
        )
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
            (f"У вас уже {limit} активных (лимит {plan.upper()}). Отключите одно или откройте PRO."),
        )
        return
    if status == "error":
        await msg.reply_text("⚠️ Не удалось сохранить напоминание.")
        return

    if rem is not None:
        job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
        if job_queue is not None:
            with SessionLocal() as session:
                user_obj = session.get(User, user_id)
            if user_obj is None:
                logger.warning("User %s not found for rescheduling reminder %s", user_id, rem.id)
            else:
                _reschedule_job(job_queue, rem, user_obj)
            logger.debug("Job queue present; suppressed reminder_saved event for %s", rem.id)
        else:
            await reminder_events.notify_reminder_saved(rem.id)
            logger.debug("Sent reminder_saved event for %s", rem.id)

    render_fn = cast(
        Callable[[Session, int], tuple[str, InlineKeyboardMarkup | None]],
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
    query = update.callback_query
    message: Message | None = update.message
    if message is None and query is not None and query.message is not None:
        message = cast(Message, query.message)
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
        base = f"reminder_{rid}"
        removed = _remove_jobs(job_queue, base)
        logger.info("Removed %d jobs for %s", removed, base)
    if message:
        await message.reply_text("Удалено")
    if job_queue is None:
        await reminder_events.notify_reminder_saved(rid)
        logger.debug("Sent reminder_saved event for %s", rid)
    else:
        logger.debug("Job queue present; suppressed reminder_saved event for %s", rid)


async def reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    if job is None or job.data is None:
        return
    data = cast("UserData", job.data)
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
    buttons = [InlineKeyboardButton("⏰ Отложить 10 мин", callback_data=f"remind_snooze:{rid}:10")]
    if rem.type == "sugar":
        buttons.append(InlineKeyboardButton("✅ Сделано", callback_data=f"remind_done:{rid}"))
        buttons.append(InlineKeyboardButton("✍️ Записать сахар", callback_data=f"remind_log:{rid}"))
    else:
        buttons.append(InlineKeyboardButton("✅ Сделано", callback_data=f"remind_done:{rid}"))
    keyboard = InlineKeyboardMarkup([buttons])
    logger.info("Sending reminder %s to chat %s", rid, chat_id)
    try:
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
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
            log_action = "remind_snooze"
        elif action == "remind_done":
            log_action = "done"
        elif action == "remind_log":
            log_action = "log_opened"
        else:
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
            logger.error("Failed to log reminder action %s for reminder %s", log_action, rid)
            return

    if action == "remind_snooze":
        mins = minutes or 10
        job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
        if job_queue is not None:
            schedule_once(
                job_queue,
                reminder_job,
                when=timedelta(minutes=mins),
                data={"reminder_id": rid, "chat_id": chat_id},
                name=f"reminder_{rid}_snooze",
                job_kwargs={
                    "id": f"reminder_{rid}_snooze",
                    "name": f"reminder_{rid}_snooze",
                    "replace_existing": True,
                },
            )
        try:
            await query.edit_message_text(f"⏰ Отложено на {mins} минут")

        except BadRequest as exc:
            if "Message is not modified" in str(exc):
                await query.answer()
            else:
                raise
    elif action == "remind_done":
        try:
            await query.edit_message_text("Готово ✅")
        except BadRequest as exc:
            if "Message is not modified" in str(exc):
                await query.answer()
            else:
                raise
    elif action == "remind_log":
        settings = config.get_settings()
        origin = (settings.public_origin or "").rstrip("/")
        base_url = (getattr(settings, "ui_base_url", "") or "").strip("/")
        url = f"{origin}/{base_url}/sugar" if base_url else f"{origin}/sugar"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Открыть", web_app=WebAppInfo(url))]])
        if query.message:
            await query.message.reply_text(
                "Введите уровень сахара (ммоль/л).",
                reply_markup=keyboard,
            )
        else:
            await query.answer("Нет сообщения для ответа", show_alert=True)
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
    user = update.effective_user
    if query is None or query.data is None or user is None:
        return
    if ":" not in query.data:
        await query.answer("Некорректное действие", show_alert=True)
        return
    try:
        action_raw, rid_str = query.data.split(":", 1)
    except ValueError:
        await query.answer("Некорректное действие", show_alert=True)
        return
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

    def db_action(session: Session) -> DbActionResult:
        rem = session.get(Reminder, rid)
        if not rem or rem.telegram_id != user_id:
            return DbActionResult(DbActionStatus.NOT_FOUND)
        if action == "del":
            session.delete(rem)
        elif action == "toggle":
            rem.is_enabled = not rem.is_enabled
        else:
            return DbActionResult(DbActionStatus.UNKNOWN)
        try:
            commit(session)
        except CommitError:
            logger.error("Failed to commit reminder action %s for reminder %s", action, rid)
            return DbActionResult(DbActionStatus.ERROR)
        if action == "toggle":
            session.refresh(rem)
            return DbActionResult(DbActionStatus.TOGGLE, rem)
        return DbActionResult(DbActionStatus.DELETE)

    if run_db is None:
        with SessionLocal() as session:
            result = db_action(session)
    else:
        result = cast(
            DbActionResult,
            await run_db(db_action, sessionmaker=SessionLocal),
        )
    if result.status is DbActionStatus.NOT_FOUND:
        await query.answer("Не найдено", show_alert=True)
        return
    if result.status is DbActionStatus.UNKNOWN:
        await query.answer("Неизвестное действие", show_alert=True)
        return
    if result.status is DbActionStatus.ERROR:
        return

    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
    if result.status is DbActionStatus.TOGGLE:
        rem = result.reminder
        if rem and rem.is_enabled:
            if job_queue is None:
                await reminder_events.notify_reminder_saved(rid)
                logger.debug("Sent reminder_saved event for %s", rid)
            else:
                with SessionLocal() as session:
                    user_obj = session.get(User, rem.telegram_id)
                if user_obj is None:
                    logger.warning(
                        "User %s not found for rescheduling reminder %s",
                        user_id,
                        rid,
                    )
                else:
                    _reschedule_job(job_queue, rem, user_obj)
                logger.debug(
                    "Job queue present; suppressed reminder_saved event for %s",
                    rid,
                )
        elif job_queue is not None:
            base = f"reminder_{rid}"
            removed = _remove_jobs(job_queue, base)
            logger.info("Removed %d jobs for %s", removed, base)
            logger.debug(
                "Job queue present; suppressed reminder_saved event for %s",
                rid,
            )
        else:
            await reminder_events.notify_reminder_saved(rid)
            logger.debug("Sent reminder_saved event for %s", rid)
    else:  # del
        if job_queue is not None:
            base = f"reminder_{rid}"
            removed = _remove_jobs(job_queue, base)
            logger.info("Removed %d jobs for %s", removed, base)
            logger.debug(
                "Job queue present; suppressed reminder_saved event for %s",
                rid,
            )
        else:
            await reminder_events.notify_reminder_saved(rid)
            logger.debug("Sent reminder_saved event for %s", rid)

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
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
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
        rems = session.query(Reminder).filter_by(telegram_id=user_id, type="after_meal", is_enabled=True).all()
    for rem in rems:
        minutes_after = rem.minutes_after
        if minutes_after is None:
            continue
        base = f"reminder_{rem.id}"
        removed = _remove_jobs(job_queue, base)
        if removed:
            logger.info("Removed %d job(s) for %s", removed, base)
        name = f"{base}_after"
        schedule_once(
            job_queue,
            reminder_job,
            when=timedelta(minutes=float(minutes_after)),
            data={"reminder_id": rem.id, "chat_id": user_id},
            name=name,
            job_kwargs={"id": name, "name": name, "replace_existing": True},
        )


reminder_action_handler = CallbackQueryHandler(reminder_action_cb, pattern="^rem_(del|toggle):")
reminder_webapp_handler = MessageHandler(filters.StatusUpdate.WEB_APP_DATA, reminder_webapp_save)


__all__ = [
    "schedule_reminder",
    "schedule_all",
    "create_reminder_from_preset",
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
    "create_reminder_from_preset",
]
