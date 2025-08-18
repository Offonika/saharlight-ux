from __future__ import annotations

import datetime
import logging
import re
from typing import Any, TypedDict, cast

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import SessionLocal, Entry, Profile, run_db
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.functions import (
    PatientProfile,
    calc_bolus,
    smart_input,
)
from services.api.app.diabetes.gpt_command_parser import parse_command
from services.api.app.diabetes.utils.ui import confirm_keyboard, menu_keyboard

from .alert_handlers import check_alert
from .dose_validation import _sanitize
from .reporting_handlers import render_entry, send_report
from . import UserData

logger = logging.getLogger(__name__)


class EditMessageMeta(TypedDict):
    """Metadata about the message being edited."""

    chat_id: int
    message_id: int


async def _handle_report_request(
    raw_text: str,
    user_data: UserData,
    message: Message,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
        date_from = datetime.datetime.strptime(raw_text, "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )
    except ValueError:
        await message.reply_text("❗ Некорректная дата. Используйте формат YYYY-MM-DD.")
        return True
    await send_report(update, context, date_from, "указанный период")
    user_data.pop("awaiting_report_date", None)
    return True


async def _save_entry(entry_data: dict[str, Any]) -> bool:
    """Persist an entry in the database."""

    def _db_save(session: Session) -> bool:
        entry = Entry(**entry_data)
        session.add(entry)
        return bool(commit(session))

    if not callable(run_db):
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
) -> bool:
    """Process numeric input for a pending entry."""
    pending_entry = user_data.get("pending_entry")
    edit_id = user_data.get("edit_id")
    if pending_entry is None or edit_id is not None:
        return False

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
            pending_entry["carbs_g"] = value * 12
        else:
            pending_entry["dose"] = value
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

        ok = await _save_entry(pending_entry)
        if not ok:
            await message.reply_text("⚠️ Не удалось сохранить запись.")
            return True
        sugar = pending_entry.get("sugar_before")
        if sugar is not None:
            await check_alert(update, context, sugar)
        user_data.pop("pending_entry", None)
        user_data.pop("pending_fields", None)
        xe = pending_entry.get("xe")
        dose = pending_entry.get("dose")
        xe_info = f", ХЕ {xe}" if xe is not None else ""
        dose_info = f", доза {dose} Ед." if dose is not None else ", доза —"
        sugar_info = f"сахар {sugar} ммоль/л" if sugar is not None else "сахар —"
        await message.reply_text(
            f"✅ Запись сохранена: {sugar_info}{xe_info}{dose_info}",
            reply_markup=menu_keyboard,
        )
        return True

    text = raw_text.lower()
    if (
        re.fullmatch(r"-?\d+(?:[.,]\d+)?", text)
        and pending_entry.get("sugar_before") is None
    ):
        try:
            sugar = float(text.replace(",", "."))
        except ValueError:
            await message.reply_text("Некорректное числовое значение.")
            return True
        if sugar < 0:
            await message.reply_text("Сахар не может быть отрицательным.")
            return True
        pending_entry["sugar_before"] = sugar
        if (
            pending_entry.get("carbs_g") is not None
            or pending_entry.get("xe") is not None
        ):
            xe_val = pending_entry.get("xe")
            carbs_g = pending_entry.get("carbs_g")
            if carbs_g is None and xe_val is not None:
                carbs_g = xe_val * 12
                pending_entry["carbs_g"] = carbs_g
            if not callable(run_db):
                with SessionLocal() as session:
                    profile = session.get(Profile, user_id)
            else:
                profile = await run_db(
                    lambda s: s.get(Profile, user_id), sessionmaker=SessionLocal
                )
            if (
                profile is not None
                and profile.icr is not None
                and profile.cf is not None
                and profile.target_bg is not None
            ):
                patient = PatientProfile(
                    icr=profile.icr, cf=profile.cf, target_bg=profile.target_bg
                )
                dose = calc_bolus(carbs_g, sugar, patient)
                pending_entry["dose"] = dose
                await message.reply_text(
                    f"💉\u202fРасчёт дозы: {dose}\u202fЕд.\nСахар: {sugar}\u202fммоль/л",
                    reply_markup=confirm_keyboard(),
                )
                return True
        await message.reply_text(
            "Введите количество углеводов или ХЕ.", reply_markup=menu_keyboard
        )
        return True

    # not handled here
    return False


async def _handle_edit_entry(
    raw_text: str,
    user_data: UserData,
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Apply edits to an existing entry."""
    edit_id = user_data.get("edit_id")
    if edit_id is None:
        return False
    text = raw_text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        await message.reply_text("Введите значение числом.")
        return True
    if value < 0:
        await message.reply_text("Значение не может быть отрицательным.")
        return True
    field = cast(str | None, user_data.get("edit_field"))

    def db_edit(session: Session) -> Entry | None:
        entry = session.get(Entry, edit_id)
        if entry is None:
            return None
        if field == "sugar":
            entry.sugar_before = value
        elif field == "xe":
            entry.xe = value
        else:
            entry.dose = value
        if not commit(session):
            return None
        session.refresh(entry)
        return entry

    if not callable(run_db):
        with SessionLocal() as session:
            entry = db_edit(session)
    else:
        entry = await run_db(db_edit, sessionmaker=SessionLocal)
    if entry is None:
        await message.reply_text("⚠️ Не удалось сохранить запись.")
        return True
    edit_info_raw = user_data.get("edit_entry")
    if not isinstance(edit_info_raw, dict):
        return True
    edit_info = cast(EditMessageMeta, edit_info_raw)
    chat_id = edit_info["chat_id"]
    message_id = edit_info["message_id"]
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Изменить", callback_data=f"edit:{entry.id}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"del:{entry.id}"),
            ]
        ]
    )
    render_text = render_entry(entry)
    await context.bot.edit_message_text(
        render_text,
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
        parse_mode="HTML",
    )
    edit_query = cast(CallbackQuery | None, user_data.get("edit_query"))
    if edit_query is not None:
        await edit_query.answer("Изменено")
    for key in ("edit_id", "edit_field", "edit_entry", "edit_query"):
        user_data.pop(key, None)
    return True


async def _handle_smart_input(
    raw_text: str,
    user_data: UserData,
    message: Message,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> None:
    """Process smart input or GPT command."""
    try:
        quick = smart_input(raw_text)
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

    carbs_match = re.search(
        r"(?:carbs|углеводов)\s*=\s*(-?\d+(?:[.,]\d+)?)", raw_text, re.I
    )
    pending_entry = user_data.get("pending_entry")
    edit_id = user_data.get("edit_id")
    if (
        pending_entry is not None
        and edit_id is None
        and (any(v is not None for v in quick.values()) or carbs_match)
    ):
        if quick["sugar"] is not None:
            pending_entry["sugar_before"] = quick["sugar"]
        if quick["xe"] is not None:
            pending_entry["xe"] = quick["xe"]
            pending_entry["carbs_g"] = quick["xe"] * 12
        elif carbs_match:
            pending_entry["carbs_g"] = float(carbs_match.group(1).replace(",", "."))
        if quick["dose"] is not None:
            pending_entry["dose"] = quick["dose"]
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
            return

        ok = await _save_entry(pending_entry)
        if not ok:
            await message.reply_text("⚠️ Не удалось сохранить запись.")
            return
        sugar = pending_entry.get("sugar_before")
        if sugar is not None:
            await check_alert(update, context, sugar)
        user_data.pop("pending_entry", None)
        user_data.pop("pending_fields", None)
        xe = pending_entry.get("xe")
        dose = pending_entry.get("dose")
        xe_info = f", ХЕ {xe}" if xe is not None else ""
        dose_info = f", доза {dose} Ед." if dose is not None else ", доза —"
        sugar_info = f"сахар {sugar} ммоль/л" if sugar is not None else "сахар —"
        await message.reply_text(
            f"✅ Запись сохранена: {sugar_info}{xe_info}{dose_info}",
            reply_markup=menu_keyboard,
        )
        return

    if any(v is not None for v in quick.values()):
        sugar = quick["sugar"]
        xe = quick["xe"]
        dose = quick["dose"]
        if any(v is not None and v < 0 for v in (sugar, xe, dose)):
            await message.reply_text("Значения не могут быть отрицательными.")
            return
        entry_data = {
            "telegram_id": user_id,
            "event_time": datetime.datetime.now(datetime.timezone.utc),
            "sugar_before": sugar,
            "xe": xe,
            "dose": dose,
            "carbs_g": xe * 12 if xe is not None else None,
        }
        missing = [f for f in ("sugar", "xe", "dose") if quick[f] is None]
        user_data["pending_entry"] = entry_data
        user_data["pending_fields"] = missing
        if not missing:
            ok = await _save_entry(entry_data)
            if not ok:
                await message.reply_text("⚠️ Не удалось сохранить запись.")
                return
            if sugar is not None:
                await check_alert(update, context, sugar)
            user_data.pop("pending_entry", None)
            user_data.pop("pending_fields", None)
            await message.reply_text(
                f"✅ Запись сохранена: сахар {sugar} ммоль/л, ХЕ {xe}, доза {dose} Ед.",
                reply_markup=menu_keyboard,
            )
            return
        next_field = missing[0]
        if next_field == "sugar":
            await message.reply_text("Введите уровень сахара (ммоль/л).")
        elif next_field == "xe":
            await message.reply_text("Введите количество ХЕ.")
        else:
            await message.reply_text("Введите дозу инсулина (ед.).")
        return

    parsed = await parse_command(raw_text)
    logger.info("FREEFORM parsed=%s", parsed)
    if not parsed or parsed.get("action") != "add_entry":
        await message.reply_text("Не понял, воспользуйтесь /help или кнопками меню")
        return

    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        await message.reply_text("Не удалось распознать данные, попробуйте ещё раз.")
        return
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
        return
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
            event_dt = datetime.datetime.combine(
                today, datetime.time(hh, mm), tzinfo=datetime.timezone.utc
            )
        except (ValueError, TypeError):
            await message.reply_text(
                "⏰ Неверный формат времени. Использую текущее время."
            )
            event_dt = datetime.datetime.now(datetime.timezone.utc)
    else:
        event_dt = datetime.datetime.now(datetime.timezone.utc)
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

    reply = (
        f"💉 Расчёт завершён:\n\n{date_str}  \n- {lines}\n\nСохранить это в дневник?"
    )
    await message.reply_text(text=reply, reply_markup=confirm_keyboard())


async def freeform_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle freeform text commands for adding diary entries."""
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

    if await _handle_report_request(raw_text, user_data, message, update, context):
        return
    if await _handle_pending_entry(
        raw_text, user_data, message, update, context, user_id
    ):
        return
    if await _handle_edit_entry(raw_text, user_data, message, context):
        return
    await _handle_smart_input(raw_text, user_data, message, update, context, user_id)


async def chat_with_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder GPT chat handler."""
    message = update.message
    if message is None:
        return
    await message.reply_text("🗨️ Чат с GPT временно недоступен.")


__all__ = ["SessionLocal", "freeform_handler", "chat_with_gpt"]
