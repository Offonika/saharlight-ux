"""GPT-based diary and chat handlers."""

from __future__ import annotations

import asyncio
import datetime
import logging
import math
import re
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar, cast

import httpx
from openai import OpenAIError
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes.services.db import SessionLocal, Entry, Profile
from services.api.app.diabetes.services.repository import CommitError, commit as _commit
from services.api.app.diabetes.utils.calc_bolus import (
    PatientProfile,
    calc_bolus,
)
from .. import assistant_state, prompts
from services.api.app.diabetes.utils.functions import smart_input
from services.api.app.diabetes.gpt_command_parser import (
    ParserTimeoutError,
    parse_command,
)
from services.api.app.diabetes.utils.constants import XE_GRAMS
from services.api.app.diabetes.utils.ui import confirm_keyboard
from services.api.app.ui.keyboard import build_main_keyboard
from services.api.app.diabetes.services import gpt_client
from services.api.app.config import settings
from services.api.app.assistant.services import memory_service
from .registration import GPT_MODE_KEY, MODE_DISCLAIMED_KEY

from .alert_handlers import check_alert as _check_alert
from .dose_validation import _sanitize
from .reporting_handlers import EntryLike, render_entry, send_report
from . import EntryData, UserData, EditMessageMeta

commit = _commit
check_alert = _check_alert

T = TypeVar("T")


class RunDB(Protocol):
    def __call__(self, fn: Callable[[Session], T], *args: object, **kwargs: object) -> Awaitable[T]: ...


logger = logging.getLogger(__name__)

run_db: RunDB | None
try:
    from services.api.app.diabetes.services.db import run_db as _run_db
except ImportError:  # pragma: no cover - optional db runner
    logger.info("run_db is unavailable; proceeding without async DB runner")
    run_db = None
else:
    run_db = cast(RunDB, _run_db)


async def _handle_report_request(
    raw_text: str,
    user_data: UserData,
    message: Message,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    menu_keyboard: ReplyKeyboardMarkup | None,
    send_report: Callable[
        [Update, ContextTypes.DEFAULT_TYPE, datetime.datetime, str],
        Awaitable[object],
    ],
) -> bool:
    """Handle the awaiting report date flow."""
    if not user_data.get("awaiting_report_date"):
        return False
    text = raw_text.lower()
    if "назад" in text or text == "/cancel":
        user_data.pop("awaiting_report_date", None)
        await message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard)
        return True
    try:
        date_from = datetime.datetime.strptime(raw_text, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        await message.reply_text("❗ Некорректная дата. Используйте формат YYYY-MM-DD.")
        return True
    await send_report(update, context, date_from, "указанный период")
    user_data.pop("awaiting_report_date", None)
    return True


async def _save_entry(
    entry_data: EntryData,
    *,
    SessionLocal: sessionmaker[Session],
    commit: Callable[[Session], None],
) -> bool:
    """Persist an entry in the database."""

    def _db_save(session: Session) -> bool:
        entry = Entry(**entry_data)
        session.add(entry)
        try:
            commit(session)
        except CommitError:
            return False
        return True

    if run_db is None:
        with SessionLocal() as session:
            return _db_save(session)
    return await run_db(_db_save, sessionmaker=SessionLocal)


async def _handle_pending_entry(
    raw_text: str,
    user_data: UserData,
    message: Message,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    *,
    SessionLocal: sessionmaker[Session],
    commit: Callable[[Session], None],
    check_alert: Callable[[Update, ContextTypes.DEFAULT_TYPE, float], Awaitable[object]],
    menu_keyboard: ReplyKeyboardMarkup | None,
) -> bool:
    """Process numeric input for a pending entry."""
    pending_raw = user_data.get("pending_entry")
    edit_id = user_data.get("edit_id")
    if not isinstance(pending_raw, dict) or edit_id is not None:
        return False
    pending_entry: EntryData = pending_raw

    pending_fields = user_data.get("pending_fields")
    if pending_fields:
        field = pending_fields[0]
        text = raw_text.replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            if field == "sugar":
                await message.reply_text("Введите сахар числом в ммоль/л.")
            elif field == "xe":
                await message.reply_text("Введите число ХЕ.")
            else:
                await message.reply_text("Введите дозу инсулина числом.")
            return True
        if not math.isfinite(value):
            if field == "sugar":
                await message.reply_text("Введите сахар числом в ммоль/л.")
            elif field == "xe":
                await message.reply_text("Введите число ХЕ.")
            else:
                await message.reply_text("Введите дозу инсулина числом.")
            return True
        if value < 0:
            if field == "sugar":
                await message.reply_text("Сахар не может быть отрицательным.")
            elif field == "xe":
                await message.reply_text("Количество ХЕ не может быть отрицательным.")
            else:
                await message.reply_text("Доза инсулина не может быть отрицательной.")
            return True
        if field == "sugar":
            pending_entry["sugar_before"] = value
        elif field == "xe":
            pending_entry["xe"] = value
            pending_entry["carbs_g"] = XE_GRAMS * value
        else:
            pending_entry["dose"] = value
            pending_entry["insulin_short"] = value
        pending_fields.pop(0)
        if pending_fields:
            next_field = pending_fields[0]
            if next_field == "sugar":
                await message.reply_text("Введите уровень сахара (ммоль/л).")
            elif next_field == "xe":
                await message.reply_text("Введите количество ХЕ.")
            else:
                await message.reply_text("Введите дозу инсулина (ед.).")
            return True

        ok = await _save_entry(pending_entry, SessionLocal=SessionLocal, commit=commit)
        if not ok:
            await message.reply_text("⚠️ Не удалось сохранить запись.")
            return True
        sugar = pending_entry.get("sugar_before")
        if sugar is not None:
            await check_alert(update, context, sugar)
        user_data.pop("pending_entry", None)
        user_data.pop("pending_fields", None)
        xe = pending_entry.get("xe")
        dose = pending_entry.get("insulin_short")
        if dose is None:
            dose = pending_entry.get("dose")
        long_dose = pending_entry.get("insulin_long")
        xe_info = f", ХЕ {xe}" if xe is not None else ""
        dose_parts: list[str] = []
        if dose is not None:
            dose_parts.append(f"короткий {dose} Ед")
        if long_dose is not None:
            dose_parts.append(f"длинный {long_dose} Ед")
        if dose_parts:
            dose_info = ", ".join(dose_parts)
            dose_info = f", {dose_info}"
        else:
            dose_info = ", доза —"
        sugar_info = f"сахар {sugar} ммоль/л" if sugar is not None else "сахар —"
        await message.reply_text(
            f"✅ Запись сохранена: {sugar_info}{xe_info}{dose_info}",
            reply_markup=menu_keyboard,
        )
        return True

    text = raw_text.lower()
    if re.fullmatch(r"-?\d+(?:[.,]\d+)?", text) and pending_entry.get("sugar_before") is None:
        try:
            sugar = float(text.replace(",", "."))
        except ValueError:
            await message.reply_text("Некорректное числовое значение.")
            return True
        if sugar < 0:
            await message.reply_text("Сахар не может быть отрицательным.")
            return True
        pending_entry["sugar_before"] = sugar
        if pending_entry.get("carbs_g") is not None or pending_entry.get("xe") is not None:
            xe_val = pending_entry.get("xe")
            carbs_g = pending_entry.get("carbs_g")
            if carbs_g is None and xe_val is not None:
                carbs_g = XE_GRAMS * xe_val
                pending_entry["carbs_g"] = carbs_g
            if carbs_g is None:
                await message.reply_text(
                    "Введите количество углеводов или ХЕ.",
                    reply_markup=menu_keyboard,
                )
                return True

            def _get_profile(session: Session) -> Profile | None:
                return cast(
                    Profile | None,
                    session.get(Profile, user_id),
                )

            if run_db is None:
                with SessionLocal() as session:
                    profile = _get_profile(session)
            else:
                profile = await run_db(_get_profile, sessionmaker=SessionLocal)
            if (
                profile is not None
                and profile.icr is not None
                and profile.cf is not None
                and profile.target_bg is not None
            ):
                patient = PatientProfile(icr=profile.icr, cf=profile.cf, target_bg=profile.target_bg)
                dose = calc_bolus(carbs_g, sugar, patient)
                pending_entry["dose"] = dose
                pending_entry["insulin_short"] = dose
                await message.reply_text(
                    f"💉\u202fРасчёт дозы: {dose}\u202fЕд.\nСахар: {sugar}\u202fммоль/л",
                    reply_markup=confirm_keyboard(),
                )
                return True
        await message.reply_text("Введите количество углеводов или ХЕ.", reply_markup=menu_keyboard)
        return True

    # not handled here
    return False


async def _handle_edit_entry(
    raw_text: str,
    user_data: UserData,
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    SessionLocal: sessionmaker[Session],
    commit: Callable[[Session], None],
) -> bool:
    """Apply edits to an existing entry."""
    edit_id = user_data.get("edit_id")
    if edit_id is None:
        return False
    edit_query_raw = user_data.get("edit_query")
    text = raw_text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        await message.reply_text("Введите значение числом.")
        return True
    if value < 0:
        await message.reply_text("Значение не может быть отрицательным.")
        return True
    field_obj = user_data.get("edit_field")
    field: str | None = field_obj if isinstance(field_obj, str) else None

    def db_edit(session: Session) -> Entry | None:
        entry = cast(Entry | None, session.get(Entry, edit_id))
        if entry is None:
            return None
        if field == "sugar":
            entry.sugar_before = value
        elif field == "xe":
            entry.xe = value
        else:
            entry.dose = value
            entry.insulin_short = value
        try:
            commit(session)
        except CommitError:
            return None
        session.refresh(entry)
        return entry

    if run_db is None:
        with SessionLocal() as session:
            entry = db_edit(session)
    else:
        entry = await run_db(db_edit, sessionmaker=SessionLocal)
    if entry is None:
        await message.reply_text("⚠️ Не удалось сохранить запись.")
        return True
    if not isinstance(edit_query_raw, dict):
        for key in ("edit_id", "edit_field", "edit_entry", "edit_query"):
            user_data.pop(key, None)  # type: ignore[misc]
        return False
    edit_query = cast(EditMessageMeta, edit_query_raw)
    chat_id = edit_query["chat_id"]
    message_id = edit_query["message_id"]
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Изменить", callback_data=f"edit:{entry.id}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"del:{entry.id}"),
            ]
        ]
    )
    render_text = render_entry(cast(EntryLike, entry))
    await context.bot.edit_message_text(
        render_text,
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode="HTML",
    )
    for key in ("edit_id", "edit_field", "edit_entry", "edit_query"):
        user_data.pop(key, None)  # type: ignore[misc]
    return True


def parse_quick_values(
    raw_text: str, *, smart_input: Callable[[str], dict[str, float | None]]
) -> tuple[dict[str, float | None], float | None]:
    """Parse quick values (sugar/xe/dose) and carbs."""
    quick = smart_input(raw_text)
    carbs_match = re.search(r"(?:carbs|углеводов)\s*=\s*(-?\d+(?:[.,]\d+)?)", raw_text, re.I)
    carbs_val = float(carbs_match.group(1).replace(",", ".")) if carbs_match else None
    return quick, carbs_val


async def apply_pending_entry(
    quick: dict[str, float | None],
    carbs_g: float | None,
    *,
    user_data: UserData,
    message: Message,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    SessionLocal: sessionmaker[Session],
    commit: Callable[[Session], None],
    check_alert: Callable[[Update, ContextTypes.DEFAULT_TYPE, float], Awaitable[object]],
    menu_keyboard: ReplyKeyboardMarkup | None,
) -> bool:
    """Apply quick values to pending entry or create a new one."""
    pending_raw = user_data.get("pending_entry")
    edit_id = user_data.get("edit_id")
    if (
        isinstance(pending_raw, dict)
        and edit_id is None
        and (any(v is not None for v in quick.values()) or carbs_g is not None)
    ):
        pending_entry: EntryData = pending_raw
        if quick["sugar"] is not None:
            pending_entry["sugar_before"] = quick["sugar"]
        if quick["xe"] is not None:
            pending_entry["xe"] = quick["xe"]
            pending_entry["carbs_g"] = XE_GRAMS * quick["xe"]
        elif carbs_g is not None:
            if carbs_g < 0:
                await message.reply_text("Количество углеводов не может быть отрицательным.")
                return True
            pending_entry["carbs_g"] = carbs_g
        if quick["dose"] is not None:
            pending_entry["dose"] = quick["dose"]
            pending_entry["insulin_short"] = quick["dose"]
        missing = [
            f
            for f, key in (
                ("sugar", "sugar_before"),
                ("xe", "xe"),
                ("dose", "dose"),
            )
            if pending_entry.get(key) is None
        ]
        user_data["pending_entry"] = pending_entry
        user_data["pending_fields"] = missing
        if missing:
            next_field = missing[0]
            if next_field == "sugar":
                await message.reply_text("Введите уровень сахара (ммоль/л).")
            elif next_field == "xe":
                await message.reply_text("Введите количество ХЕ.")
            else:
                await message.reply_text("Введите дозу инсулина (ед.).")
            return True
        ok = await _save_entry(pending_entry, SessionLocal=SessionLocal, commit=commit)
        if not ok:
            await message.reply_text("⚠️ Не удалось сохранить запись.")
            return True
        sugar = pending_entry.get("sugar_before")
        if sugar is not None:
            await check_alert(update, context, sugar)
        user_data.pop("pending_entry", None)
        user_data.pop("pending_fields", None)
        xe = pending_entry.get("xe")
        dose = pending_entry.get("insulin_short")
        if dose is None:
            dose = pending_entry.get("dose")
        long_dose = pending_entry.get("insulin_long")
        xe_info = f", ХЕ {xe}" if xe is not None else ""
        dose_parts = []
        if dose is not None:
            dose_parts.append(f"короткий {dose} Ед")
        if long_dose is not None:
            dose_parts.append(f"длинный {long_dose} Ед")
        if dose_parts:
            dose_info = f", {', '.join(dose_parts)}"
        else:
            dose_info = ", доза —"
        sugar_info = f"сахар {sugar} ммоль/л" if sugar is not None else "сахар —"
        await message.reply_text(
            f"✅ Запись сохранена: {sugar_info}{xe_info}{dose_info}",
            reply_markup=menu_keyboard,
        )
        return True

    if any(v is not None for v in quick.values()):
        sugar = quick["sugar"]
        xe = quick["xe"]
        dose = quick["dose"]
        if any(v is not None and v < 0 for v in (sugar, xe, dose)):
            await message.reply_text("Значения не могут быть отрицательными.")
            return True
        entry_data: EntryData = {
            "telegram_id": user_id,
            "event_time": datetime.datetime.now(datetime.timezone.utc),
            "sugar_before": sugar,
            "xe": xe,
            "dose": dose,
            "insulin_short": dose,
            "carbs_g": XE_GRAMS * xe if xe is not None else None,
        }
        missing = [f for f in ("sugar", "xe", "dose") if quick[f] is None]
        user_data["pending_entry"] = entry_data
        user_data["pending_fields"] = missing
        if not missing:
            ok = await _save_entry(entry_data, SessionLocal=SessionLocal, commit=commit)
            if not ok:
                await message.reply_text("⚠️ Не удалось сохранить запись.")
                return True
            if sugar is not None:
                await check_alert(update, context, sugar)
            user_data.pop("pending_entry", None)
            user_data.pop("pending_fields", None)
            short_info = f"короткий {dose} Ед." if dose is not None else "короткий —"
            await message.reply_text(
                f"✅ Запись сохранена: сахар {sugar} ммоль/л, ХЕ {xe}, {short_info}",
                reply_markup=menu_keyboard,
            )
            return True
        next_field = missing[0]
        if next_field == "sugar":
            await message.reply_text("Введите уровень сахара (ммоль/л).")
        elif next_field == "xe":
            await message.reply_text("Введите количество ХЕ.")
        else:
            await message.reply_text("Введите дозу инсулина (ед.).")
        return True

    return False


async def parse_via_gpt(
    raw_text: str,
    message: Message,
    *,
    parse_command: Callable[[str], Awaitable[dict[str, object] | None]],
    on_unrecognized: Callable[[], Awaitable[None]] | None = None,
) -> tuple[datetime.datetime, dict[str, float | None]] | None:
    """Parse freeform text via GPT parser."""
    try:
        parsed = await parse_command(raw_text)
    except ParserTimeoutError:
        await message.reply_text("Парсер недоступен, попробуйте позже")
        return None
    logger.info("FREEFORM parsed=%s", parsed)
    if not parsed or parsed.get("action") != "add_entry":
        if on_unrecognized is not None:
            await on_unrecognized()
        else:
            await message.reply_text("Не понял, воспользуйтесь /help или кнопками меню")
        return None
    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        await message.reply_text("Не удалось распознать данные, попробуйте ещё раз.")
        return None
    if any(
        v is not None and v < 0
        for v in (
            fields.get("xe"),
            fields.get("carbs_g"),
            fields.get("dose"),
            fields.get("sugar_before"),
        )
    ):
        await message.reply_text("Значения не могут быть отрицательными.")
        return None
    entry_date_obj = parsed.get("entry_date")
    time_obj = parsed.get("time")
    if isinstance(entry_date_obj, str):
        try:
            event_dt = datetime.datetime.fromisoformat(entry_date_obj)
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=datetime.timezone.utc)
            else:
                event_dt = event_dt.astimezone(datetime.timezone.utc)
        except ValueError:
            event_dt = datetime.datetime.now(datetime.timezone.utc)
    elif isinstance(time_obj, str):
        try:
            hh, mm = map(int, time_obj.split(":"))
            today = datetime.datetime.now(datetime.timezone.utc).date()
            event_dt = datetime.datetime.combine(today, datetime.time(hh, mm), tzinfo=datetime.timezone.utc)
        except (ValueError, TypeError):
            await message.reply_text("⏰ Неверный формат времени. Использую текущее время.")
            event_dt = datetime.datetime.now(datetime.timezone.utc)
    else:
        event_dt = datetime.datetime.now(datetime.timezone.utc)
    clean_fields: dict[str, float | None] = {
        "xe": cast(float | None, fields.get("xe")),
        "carbs_g": cast(float | None, fields.get("carbs_g")),
        "dose": cast(float | None, fields.get("dose")),
        "sugar_before": cast(float | None, fields.get("sugar_before")),
    }
    return event_dt, clean_fields


async def finalize_entry(
    fields: dict[str, float | None],
    event_dt: datetime.datetime,
    user_id: int,
    user_data: UserData,
    message: Message,
) -> None:
    """Store parsed entry and ask user for confirmation."""
    user_data.pop("pending_entry", None)
    user_data["pending_entry"] = {
        "telegram_id": user_id,
        "event_time": event_dt,
        "xe": fields.get("xe"),
        "carbs_g": fields.get("carbs_g"),
        "dose": fields.get("dose"),
        "sugar_before": fields.get("sugar_before"),
        "photo_path": None,
    }
    pending_entry = user_data["pending_entry"]
    xe_val: float | None = pending_entry.get("xe")
    carbs_val: float | None = pending_entry.get("carbs_g")
    dose_val: float | None = pending_entry.get("dose")
    sugar_val: float | None = pending_entry.get("sugar_before")
    date_str = event_dt.strftime("%d.%m %H:%M")
    xe_part = f"{xe_val}\u202fХЕ" if xe_val is not None else ""
    carb_part = f"{carbs_val:.0f}\u202fг углеводов" if carbs_val is not None else ""
    dose_part = f"Инсулин: {dose_val}\u202fед" if dose_val is not None else ""
    sugar_part = f"Сахар: {sugar_val}\u202fммоль/л" if sugar_val is not None else ""
    lines = "  \n- ".join(filter(None, [xe_part or carb_part, dose_part, sugar_part]))
    reply = f"💉 Расчёт завершён:\n\n{date_str}  \n- {lines}\n\nСохранить это в дневник?"
    await message.reply_text(text=reply, reply_markup=confirm_keyboard())


async def freeform_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    SessionLocal: sessionmaker[Session] | None = None,
    commit: Callable[[Session], None] | None = None,
    check_alert: (Callable[[Update, ContextTypes.DEFAULT_TYPE, float], Awaitable[object]] | None) = None,
    menu_keyboard_markup: ReplyKeyboardMarkup | None = None,
    smart_input: Callable[[str], dict[str, float | None]] = smart_input,
    parse_command: Callable[[str], Awaitable[dict[str, object] | None]] = parse_command,
    send_report: Callable[
        [Update, ContextTypes.DEFAULT_TYPE, datetime.datetime, str],
        Awaitable[object],
    ] = send_report,
) -> None:
    """Handle freeform text commands for adding diary entries."""
    SessionLocal = SessionLocal or globals()["SessionLocal"]
    commit = commit or globals()["commit"]
    check_alert = check_alert or globals()["check_alert"]
    menu_keyboard_markup = menu_keyboard_markup or build_main_keyboard()
    if SessionLocal is None:
        raise RuntimeError("SessionLocal sessionmaker is required")
    if commit is None:
        raise RuntimeError("commit function is required")
    if check_alert is None:
        raise RuntimeError("check_alert callback is required")
    user_data_raw = context.user_data
    if user_data_raw is None:
        return
    user_data = cast(UserData, user_data_raw)
    message = update.message
    if message is None:
        return
    text = message.text
    if text is None:
        return
    user = update.effective_user
    if user is None:
        return
    raw_text = text.strip()
    user_id = user.id
    logger.info("FREEFORM raw='%s'  user=%s", _sanitize(raw_text), user_id)

    last_mode_obj = user_data.get(assistant_state.LAST_MODE_KEY)
    chat_active = bool(user_data.get(GPT_MODE_KEY)) or last_mode_obj == "chat"
    if chat_active:
        async def _continue_chat() -> None:
            await chat_with_gpt(update, context)

        parsed_entry = await parse_via_gpt(
            raw_text,
            message,
            parse_command=parse_command,
            on_unrecognized=_continue_chat,
        )
        if parsed_entry is None:
            return
        event_dt, fields = parsed_entry
        await finalize_entry(fields, event_dt, user_id, user_data, message)
        return

    if await _handle_report_request(
        raw_text,
        user_data,
        message,
        update,
        context,
        menu_keyboard=menu_keyboard_markup,
        send_report=send_report,
    ):
        return
    if await _handle_pending_entry(
        raw_text,
        user_data,
        message,
        update,
        context,
        user_id,
        SessionLocal=SessionLocal,
        commit=commit,
        check_alert=check_alert,
        menu_keyboard=menu_keyboard_markup,
    ):
        return
    if await _handle_edit_entry(
        raw_text,
        user_data,
        message,
        context,
        SessionLocal=SessionLocal,
        commit=commit,
    ):
        return
    try:
        quick, carbs_g = parse_quick_values(raw_text, smart_input=smart_input)
    except ValueError as exc:
        msg = str(exc)
        if "mismatched unit for sugar" in msg:
            await message.reply_text("❗ Сахар указывается в ммоль/л, не в XE.")
        elif "mismatched unit for dose" in msg:
            await message.reply_text("❗ Доза указывается в ед., не в ммоль.")
        elif "mismatched unit for xe" in msg:
            await message.reply_text("❗ ХЕ указываются числом, без ммоль/л и ед.")
        else:
            await message.reply_text(
                "Не удалось распознать значения, используйте сахар=5 xe=1 dose=2",
            )
        return
    if await apply_pending_entry(
        quick,
        carbs_g,
        user_data=user_data,
        message=message,
        update=update,
        context=context,
        user_id=user_id,
        SessionLocal=SessionLocal,
        commit=commit,
        check_alert=check_alert,
        menu_keyboard=menu_keyboard_markup,
    ):
        return
    parsed = await parse_via_gpt(
        raw_text,
        message,
        parse_command=parse_command,
    )
    if parsed is None:
        return
    event_dt, fields = parsed
    await finalize_entry(fields, event_dt, user_id, user_data, message)


async def chat_with_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Chat handler that records conversation history."""

    message = update.message
    if message is None or message.text is None:
        return
    if not settings.assistant_mode_enabled:
        return

    user = update.effective_user
    user_data = cast(dict[str, object], context.user_data)
    user_text = message.text

    history = cast(list[str], user_data.get(assistant_state.HISTORY_KEY, []))[-assistant_state.ASSISTANT_MAX_TURNS :]
    messages: list[dict[str, str]] = []
    summary = cast(str | None, user_data.get(assistant_state.SUMMARY_KEY))
    if summary:
        messages.append({"role": "system", "content": summary})
    for turn in history:
        user_part, _, assistant_part = turn.partition("\nassistant: ")
        if user_part.startswith("user: "):
            user_part = user_part[6:]
        messages.append({"role": "user", "content": user_part})
        if assistant_part:
            messages.append({"role": "assistant", "content": assistant_part})
    messages.append({"role": "user", "content": user_text})

    try:
        completion = await gpt_client.create_chat_completion(
            model="gpt-4o-mini",
            messages=messages,
        )
        content = completion.choices[0].message.content or ""
        reply = gpt_client.format_reply(content)
    except OpenAIError as exc:
        logger.exception("Failed to get GPT reply: %s", exc)
        reply = "⚠️ Не удалось получить ответ. Попробуйте позже."
    except httpx.HTTPError as exc:
        logger.exception("Failed to get GPT reply: %s", exc)
        reply = "⚠️ Не удалось получить ответ. Попробуйте позже."
    except asyncio.TimeoutError as exc:
        logger.exception("GPT request timed out: %s", exc)
        reply = "⚠️ Не удалось получить ответ. Попробуйте позже."

    if not user_data.get(MODE_DISCLAIMED_KEY):
        reply = f"{prompts.disclaimer()}\n\n{reply}"
        user_data[MODE_DISCLAIMED_KEY] = True

    await message.reply_text(reply)
    summarized = assistant_state.add_turn(user_data, f"user: {user_text}\nassistant: {reply}")
    if user is not None:
        summary = cast(str | None, user_data.get(assistant_state.SUMMARY_KEY)) if summarized else None
        await memory_service.record_turn(user.id, summary_text=summary)


__all__ = [
    "SessionLocal",
    "freeform_handler",
    "chat_with_gpt",
    "ParserTimeoutError",
    "parse_quick_values",
    "apply_pending_entry",
    "parse_via_gpt",
    "finalize_entry",
]
