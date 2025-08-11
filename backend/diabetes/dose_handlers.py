"""Handlers for insulin dose calculations and related utilities."""

from __future__ import annotations

import logging
import datetime
import asyncio
import os
import re
from pathlib import Path

from openai import OpenAIError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from diabetes.db import SessionLocal, User, Entry, Profile
from diabetes.functions import (
    extract_nutrition_info,
    calc_bolus,
    PatientProfile,
    smart_input,
)
from diabetes.gpt_client import create_thread, send_message, _get_client
from diabetes.gpt_command_parser import parse_command
from diabetes.ui import menu_keyboard, confirm_keyboard, dose_keyboard, sugar_keyboard
from .common_handlers import commit_session, menu_command
from .alert_handlers import check_alert
from .reporting_handlers import send_report, history_view, report_request, render_entry
from .profile_handlers import profile_view


logger = logging.getLogger(__name__)


def _sanitize(text: str, max_len: int = 200) -> str:
    """Strip control chars and truncate for safe logging."""
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(text))
    return cleaned[:max_len]


DOSE_METHOD, DOSE_XE, DOSE_CARBS, DOSE_SUGAR = range(3, 7)
PHOTO_SUGAR = 7
SUGAR_VAL = 8
WAITING_GPT_FLAG = "waiting_gpt_response"


async def photo_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to send a food photo for analysis."""
    await update.message.reply_text(
        "📸 Пришлите фото блюда для анализа.", reply_markup=menu_keyboard
    )


async def sugar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for current sugar level."""
    context.user_data.pop("pending_entry", None)
    context.user_data["pending_entry"] = {
        "telegram_id": update.effective_user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    # Track that sugar conversation is active so it can be cancelled
    chat_data = getattr(context, "chat_data", None)
    if chat_data is not None:
        chat_data["sugar_active"] = True
    await update.message.reply_text(
        "Введите текущий уровень сахара (ммоль/л).", reply_markup=sugar_keyboard
    )
    return SUGAR_VAL


async def sugar_val(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the provided sugar level to the diary."""
    chat_data = getattr(context, "chat_data", None)
    if chat_data is not None and not chat_data.get("sugar_active"):
        return ConversationHandler.END
    text = update.message.text.strip().replace(",", ".")
    try:
        sugar = float(text)
    except ValueError:
        await update.message.reply_text("Введите сахар числом в ммоль/л.")
        return SUGAR_VAL
    if sugar < 0:
        await update.message.reply_text("Сахар не может быть отрицательным.")
        return SUGAR_VAL
    entry_data = context.user_data.pop("pending_entry", None) or {
        "telegram_id": update.effective_user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    entry_data["sugar_before"] = sugar
    with SessionLocal() as session:
        entry = Entry(**entry_data)
        session.add(entry)
        if not commit_session(session):
            await update.message.reply_text("⚠️ Не удалось сохранить запись.")
            return ConversationHandler.END
    await check_alert(update, context, sugar)
    await update.message.reply_text(
        f"✅ Уровень сахара {sugar} ммоль/л сохранён.",
        reply_markup=menu_keyboard,
    )
    if chat_data is not None:
        chat_data.pop("sugar_active", None)
    return ConversationHandler.END


async def dose_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for dose calculation conversation."""
    context.user_data.pop("pending_entry", None)
    context.user_data.pop("edit_id", None)
    context.user_data.pop("dose_method", None)
    await update.message.reply_text(
        "💉 Как рассчитать дозу? Выберите метод:",
        reply_markup=dose_keyboard,
    )
    return DOSE_METHOD


async def dose_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle method selection for dose calculation."""
    text = update.message.text.lower()
    if "назад" in text:
        return await dose_cancel(update, context)
    if "углев" in text:
        context.user_data["dose_method"] = "carbs"
        await update.message.reply_text("Введите количество углеводов (г).")
        return DOSE_CARBS
    if "xe" in text or "хе" in text:
        context.user_data["dose_method"] = "xe"
        await update.message.reply_text("Введите количество ХЕ.")
        return DOSE_XE
    await update.message.reply_text(
        "Пожалуйста, выберите метод: ХЕ или углеводы.",
        reply_markup=dose_keyboard,
    )
    return DOSE_METHOD


async def dose_xe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture XE amount from user."""
    text = update.message.text.strip().replace(",", ".")
    try:
        xe = float(text)
    except ValueError:
        await update.message.reply_text("Введите число ХЕ.")
        return DOSE_XE
    if xe < 0:
        await update.message.reply_text("Количество ХЕ не может быть отрицательным.")
        return DOSE_XE
    context.user_data["pending_entry"] = {
        "telegram_id": update.effective_user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "xe": xe,
    }
    await update.message.reply_text("Введите текущий сахар (ммоль/л).")
    return DOSE_SUGAR


async def dose_carbs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture carbohydrates in grams."""
    text = update.message.text.strip().replace(",", ".")
    try:
        carbs = float(text)
    except ValueError:
        await update.message.reply_text("Введите углеводы числом в граммах.")
        return DOSE_CARBS
    if carbs < 0:
        await update.message.reply_text(
            "Количество углеводов не может быть отрицательным."
        )
        return DOSE_CARBS
    context.user_data["pending_entry"] = {
        "telegram_id": update.effective_user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": carbs,
    }
    await update.message.reply_text("Введите текущий сахар (ммоль/л).")
    return DOSE_SUGAR


async def dose_sugar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalize dose calculation after receiving sugar level."""
    text = update.message.text.strip().replace(",", ".")
    try:
        sugar = float(text)
    except ValueError:
        await update.message.reply_text("Введите сахар числом в ммоль/л.")
        return DOSE_SUGAR
    if sugar < 0:
        await update.message.reply_text("Сахар не может быть отрицательным.")
        return DOSE_SUGAR

    entry = context.user_data.get("pending_entry", {})
    entry["sugar_before"] = sugar
    xe = entry.get("xe")
    carbs_g = entry.get("carbs_g")
    if carbs_g is None and xe is None:
        await update.message.reply_text(
            "Не указаны углеводы или ХЕ. Расчёт невозможен.",
            reply_markup=menu_keyboard,
        )
        context.user_data.pop("pending_entry", None)
        return ConversationHandler.END
    if carbs_g is None and xe is not None:
        carbs_g = xe * 12
        entry["carbs_g"] = carbs_g

    user_id = update.effective_user.id
    with SessionLocal() as session:
        profile = session.get(Profile, user_id)

    if not profile or None in (profile.icr, profile.cf, profile.target_bg):
        await update.message.reply_text(
            "Профиль не настроен. Установите коэффициенты через /profile.",
            reply_markup=menu_keyboard,
        )
        context.user_data.pop("pending_entry", None)
        return ConversationHandler.END

    patient = PatientProfile(
        icr=profile.icr,
        cf=profile.cf,
        target_bg=profile.target_bg,
    )
    dose = calc_bolus(carbs_g, sugar, patient)
    entry["dose"] = dose

    context.user_data["pending_entry"] = entry

    xe_info = f", ХЕ: {xe}" if xe is not None else ""
    await update.message.reply_text(
        f"💉 Расчёт завершён:\n"
        f"• Углеводы: {carbs_g} г{xe_info}\n"
        f"• Сахар: {sugar} ммоль/л\n"
        f"• Ваша доза: {dose} Ед\n\n"
        "Сохранить это в дневник?",
        reply_markup=confirm_keyboard(),
    )
    return ConversationHandler.END


async def dose_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel dose calculation conversation."""
    await update.message.reply_text("Отменено.", reply_markup=menu_keyboard)
    context.user_data.pop("pending_entry", None)
    context.user_data.pop("dose_method", None)
    chat_data = getattr(context, "chat_data", None)
    if chat_data is not None:
        chat_data.pop("sugar_active", None)
    return ConversationHandler.END


def _cancel_then(handler):
    """Return a wrapper calling ``dose_cancel`` before ``handler``."""

    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await dose_cancel(update, context)
        return await handler(update, context)

    return wrapped


async def freeform_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle freeform text commands for adding diary entries."""
    raw_text = update.message.text.strip()
    user_id = update.effective_user.id
    logging.info("FREEFORM raw='%s'  user=%s", _sanitize(raw_text), user_id)

    if context.user_data.get("awaiting_report_date"):
        text = update.message.text.strip().lower()
        if "назад" in text or text == "/cancel":
            context.user_data.pop("awaiting_report_date", None)
            await update.message.reply_text(
                "📋 Выберите действие:", reply_markup=menu_keyboard
            )
            return
        try:
            date_from = datetime.datetime.strptime(
                update.message.text.strip(), "%Y-%m-%d"
            ).replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            await update.message.reply_text(
                "❗ Некорректная дата. Используйте формат YYYY-MM-DD."
            )
            return
        await send_report(update, context, date_from, "указанный период")
        context.user_data.pop("awaiting_report_date", None)
        return

    pending_entry = context.user_data.get("pending_entry")
    pending_fields = context.user_data.get("pending_fields")
    edit_id = context.user_data.get("edit_id")
    if pending_entry is not None and edit_id is None and pending_fields:
        field = pending_fields[0]
        text = update.message.text.strip().replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            if field == "sugar":
                await update.message.reply_text(
                    "Введите сахар числом в ммоль/л."
                )
            elif field == "xe":
                await update.message.reply_text("Введите число ХЕ.")
            else:
                await update.message.reply_text(
                    "Введите дозу инсулина числом."
                )
            return
        if value < 0:
            if field == "sugar":
                await update.message.reply_text(
                    "Сахар не может быть отрицательным."
                )
            elif field == "xe":
                await update.message.reply_text(
                    "Количество ХЕ не может быть отрицательным."
                )
            else:
                await update.message.reply_text(
                    "Доза инсулина не может быть отрицательной."
                )
            return
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
                await update.message.reply_text(
                    "Введите уровень сахара (ммоль/л)."
                )
            elif next_field == "xe":
                await update.message.reply_text("Введите количество ХЕ.")
            else:
                await update.message.reply_text(
                    "Введите дозу инсулина (ед.)."
                )
            return
        with SessionLocal() as session:
            entry = Entry(**pending_entry)
            session.add(entry)
            if not commit_session(session):
                await update.message.reply_text(
                    "⚠️ Не удалось сохранить запись."
                )
                return
        sugar = pending_entry.get("sugar_before")
        if sugar is not None:
            await check_alert(update, context, sugar)
        context.user_data.pop("pending_entry", None)
        context.user_data.pop("pending_fields", None)
        xe = pending_entry.get("xe")
        dose = pending_entry.get("dose")
        xe_info = f", ХЕ {xe}" if xe is not None else ""
        dose_info = f", доза {dose} Ед." if dose is not None else ", доза —"
        sugar_info = f"сахар {sugar} ммоль/л" if sugar is not None else "сахар —"
        await update.message.reply_text(
            f"✅ Запись сохранена: {sugar_info}{xe_info}{dose_info}",
            reply_markup=menu_keyboard,
        )
        return
    if pending_entry is not None and edit_id is None:
        entry = pending_entry
        text = update.message.text.lower().strip()
        if re.fullmatch(r"-?\d+(?:[.,]\d+)?", text) and entry.get("sugar_before") is None:
            try:
                sugar = float(text.replace(",", "."))
            except ValueError:
                await update.message.reply_text(
                    "Некорректное числовое значение."
                )
                return
            if sugar < 0:
                await update.message.reply_text(
                    "Сахар не может быть отрицательным."
                )
                return
            entry["sugar_before"] = sugar
            if entry.get("carbs_g") is not None or entry.get("xe") is not None:
                xe = entry.get("xe")
                carbs_g = entry.get("carbs_g")
                if carbs_g is None and xe is not None:
                    carbs_g = xe * 12
                    entry["carbs_g"] = carbs_g
                user_id = update.effective_user.id
                with SessionLocal() as session:
                    profile = session.get(Profile, user_id)
                if not profile or None in (
                    profile.icr,
                    profile.cf,
                    profile.target_bg,
                ):
                    await update.message.reply_text(
                        "Профиль не настроен. Установите коэффициенты через /profile.",
                        reply_markup=menu_keyboard,
                    )
                    context.user_data.pop("pending_entry", None)
                    return
                patient = PatientProfile(
                    icr=profile.icr,
                    cf=profile.cf,
                    target_bg=profile.target_bg,
                )
                dose = calc_bolus(carbs_g, sugar, patient)
                entry["dose"] = dose
                context.user_data["pending_entry"] = entry
                xe_info = f", ХЕ: {xe}" if xe is not None else ""
                await update.message.reply_text(
                    f"💉 Расчёт завершён:\n"
                    f"• Углеводы: {carbs_g} г{xe_info}\n"
                    f"• Сахар: {sugar} ммоль/л\n"
                    f"• Ваша доза: {dose} Ед\n\n"
                    "Сохранить это в дневник?",
                    reply_markup=confirm_keyboard(),
                )
            else:
                await update.message.reply_text(
                    f"Сохранить уровень сахара {sugar} ммоль/л в дневник?",
                    reply_markup=confirm_keyboard(),
                )
            return
        parts = dict(
            re.findall(r"(\w+)\s*=\s*(-?\d+(?:[.,]\d+)?)(?=\s|$)", text)
        )
        if not parts:
            await update.message.reply_text("Не вижу ни одного поля для изменения.")
            return
        if "xe" in parts:
            try:
                xe_val = float(parts["xe"].replace(",", "."))
            except ValueError:
                await update.message.reply_text("Некорректное числовое значение.")
                return
            if xe_val < 0:
                await update.message.reply_text(
                    "Количество ХЕ не может быть отрицательным."
                )
                return
            entry["xe"] = xe_val
            entry["carbs_g"] = xe_val * 12
        if "carbs" in parts:
            try:
                carbs_val = float(parts["carbs"].replace(",", "."))
            except ValueError:
                await update.message.reply_text("Некорректное числовое значение.")
                return
            if carbs_val < 0:
                await update.message.reply_text(
                    "Количество углеводов не может быть отрицательным."
                )
                return
            entry["carbs_g"] = carbs_val
        if "dose" in parts:
            try:
                dose_val = float(parts["dose"].replace(",", "."))
            except ValueError:
                await update.message.reply_text("Некорректное числовое значение.")
                return
            if dose_val < 0:
                await update.message.reply_text(
                    "Доза инсулина не может быть отрицательной."
                )
                return
            entry["dose"] = dose_val
        if "сахар" in parts or "sugar" in parts:
            sugar_value = parts.get("сахар") or parts["sugar"]
            try:
                sugar_val = float(sugar_value.replace(",", "."))
            except ValueError:
                await update.message.reply_text("Некорректное числовое значение.")
                return
            if sugar_val < 0:
                await update.message.reply_text(
                    "Сахар не может быть отрицательным."
                )
                return
            entry["sugar_before"] = sugar_val
        carbs = entry.get("carbs_g")
        xe = entry.get("xe")
        sugar = entry.get("sugar_before")
        dose = entry.get("dose")
        xe_info = f", ХЕ: {xe}" if xe is not None else ""

        await update.message.reply_text(
            f"💉 Расчёт завершён:\n"
            f"• Углеводы: {carbs} г{xe_info}\n"
            f"• Сахар: {sugar} ммоль/л\n"
            f"• Ваша доза: {dose} Ед\n\n"
            f"Сохранить это в дневник?",
            reply_markup=confirm_keyboard(),
        )
        return
    if "edit_id" in context.user_data:
        field = context.user_data.get("edit_field")
        text = update.message.text.strip().replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            await update.message.reply_text("Некорректное числовое значение.")
            return
        if value < 0:
            if field == "sugar":
                await update.message.reply_text(
                    "Сахар не может быть отрицательным."
                )
            elif field == "xe":
                await update.message.reply_text(
                    "Количество ХЕ не может быть отрицательным."
                )
            else:
                await update.message.reply_text(
                    "Доза инсулина не может быть отрицательной."
                )
            return
        with SessionLocal() as session:
            entry = session.get(Entry, context.user_data["edit_id"])
            if not entry:
                await update.message.reply_text("Запись уже удалена.")
                for key in ("edit_id", "edit_field", "edit_entry", "edit_query"):
                    context.user_data.pop(key, None)
                return
            field_map = {"sugar": "sugar_before", "xe": "xe", "dose": "dose"}
            setattr(entry, field_map[field], value)
            entry.updated_at = datetime.datetime.now(datetime.timezone.utc)
            if not commit_session(session):
                await update.message.reply_text("⚠️ Не удалось обновить запись.")
                return
            session.refresh(entry)
            if field == "sugar":
                await check_alert(update, context, value)
            render_text = render_entry(entry)
        edit_info = context.user_data.get("edit_entry", {})
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✏️ Изменить", callback_data=f"edit:{context.user_data['edit_id']}"
                    ),
                    InlineKeyboardButton(
                        "🗑 Удалить", callback_data=f"del:{context.user_data['edit_id']}"
                    ),
                ]
            ]
        )
        await context.bot.edit_message_text(
            render_text,
            chat_id=edit_info.get("chat_id"),
            message_id=edit_info.get("message_id"),
            parse_mode="HTML",
            reply_markup=markup,
        )
        query = context.user_data.get("edit_query")
        if query:
            await query.answer("Изменено")
        for key in ("edit_id", "edit_field", "edit_entry", "edit_query"):
            context.user_data.pop(key, None)
        return

    try:
        quick = smart_input(raw_text)
    except ValueError as exc:
        msg = str(exc)
        if "mismatched unit for sugar" in msg:
            await update.message.reply_text(
                "❗ Сахар указывается в ммоль/л, не в XE."
            )
        elif "mismatched unit for dose" in msg:
            await update.message.reply_text(
                "❗ Доза указывается в ед., не в ммоль."
            )
        elif "mismatched unit for xe" in msg:
            await update.message.reply_text(
                "❗ ХЕ указываются числом, без ммоль/л и ед."
            )
        else:
            await update.message.reply_text(
                "Не удалось распознать значения, используйте сахар=5 xe=1 dose=2"
            )
        return
    if any(v is not None for v in quick.values()):
        sugar = quick["sugar"]
        xe = quick["xe"]
        dose = quick["dose"]
        if any(v is not None and v < 0 for v in (sugar, xe, dose)):
            await update.message.reply_text(
                "Значения не могут быть отрицательными."
            )
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
        if not missing:
            with SessionLocal() as session:
                entry = Entry(**entry_data)
                session.add(entry)
                if not commit_session(session):
                    await update.message.reply_text(
                        "⚠️ Не удалось сохранить запись."
                    )
                    return
            if sugar is not None:
                await check_alert(update, context, sugar)
            await update.message.reply_text(
                f"✅ Запись сохранена: сахар {sugar} ммоль/л, ХЕ {xe}, доза {dose} Ед.",
                reply_markup=menu_keyboard,
            )
            return
        context.user_data["pending_entry"] = entry_data
        context.user_data["pending_fields"] = missing
        next_field = missing[0]
        if next_field == "sugar":
            await update.message.reply_text("Введите уровень сахара (ммоль/л).")
        elif next_field == "xe":
            await update.message.reply_text("Введите количество ХЕ.")
        else:
            await update.message.reply_text("Введите дозу инсулина (ед.).")
        return

    parsed = await parse_command(raw_text)
    logging.info("FREEFORM parsed=%s", parsed)
    if not parsed or parsed.get("action") != "add_entry":
        await update.message.reply_text(
            "Не понял, воспользуйтесь /help или кнопками меню"
        )
        return

    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        await update.message.reply_text(
            "Не удалось распознать данные, попробуйте ещё раз."
        )
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
        await update.message.reply_text(
            "Значения не могут быть отрицательными."
        )
        return
    entry_date = parsed.get("entry_date")
    time_str = parsed.get("time")

    if entry_date:
        try:
            event_dt = datetime.datetime.fromisoformat(entry_date)
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=datetime.timezone.utc)
            else:
                event_dt = event_dt.astimezone(datetime.timezone.utc)
        except ValueError:
            event_dt = datetime.datetime.now(datetime.timezone.utc)
    elif time_str:
        try:
            hh, mm = map(int, time_str.split(":"))
            today = datetime.datetime.now(datetime.timezone.utc).date()
            event_dt = datetime.datetime.combine(
                today, datetime.time(hh, mm), tzinfo=datetime.timezone.utc
            )
        except (ValueError, TypeError):
            await update.message.reply_text(
                "⏰ Неверный формат времени. Использую текущее время."
            )
            event_dt = datetime.datetime.now(datetime.timezone.utc)
    else:
        event_dt = datetime.datetime.now(datetime.timezone.utc)
    context.user_data.pop("pending_entry", None)
    context.user_data["pending_entry"] = {
        "telegram_id": user_id,
        "event_time": event_dt,
        "xe": fields.get("xe"),
        "carbs_g": fields.get("carbs_g"),
        "dose": fields.get("dose"),
        "sugar_before": fields.get("sugar_before"),
        "photo_path": None,
    }

    xe_val = fields.get("xe")
    carbs_val = fields.get("carbs_g")
    dose_val = fields.get("dose")
    sugar_val = fields.get("sugar_before")
    date_str = event_dt.strftime("%d.%m %H:%M")
    xe_part = f"{xe_val} ХЕ" if xe_val is not None else ""
    carb_part = f"{carbs_val:.0f} г углеводов" if carbs_val is not None else ""
    dose_part = f"Инсулин: {dose_val} ед" if dose_val is not None else ""
    sugar_part = f"Сахар: {sugar_val} ммоль/л" if sugar_val is not None else ""
    lines = "  \n- ".join(filter(None, [xe_part or carb_part, dose_part, sugar_part]))

    reply = f"💉 Расчёт завершён:\n\n{date_str}  \n- {lines}\n\nСохранить это в дневник?"
    await update.message.reply_text(reply, reply_markup=confirm_keyboard())
    return ConversationHandler.END


async def chat_with_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder GPT chat handler."""
    await update.message.reply_text("🗨️ Чат с GPT временно недоступен.")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, demo: bool = False):
    """Process food photos and trigger nutrition analysis."""
    message = update.message or update.callback_query.message
    user_id = update.effective_user.id

    if context.user_data.get(WAITING_GPT_FLAG):
        await message.reply_text("⏳ Уже обрабатываю фото, подождите…")
        return ConversationHandler.END
    context.user_data[WAITING_GPT_FLAG] = True

    file_path = context.user_data.pop("__file_path", None)
    if not file_path:
        try:
            photo = update.message.photo[-1]
        except (AttributeError, IndexError, TypeError):
            await message.reply_text("❗ Файл не распознан как изображение.")
            context.user_data.pop(WAITING_GPT_FLAG, None)
            return ConversationHandler.END

        os.makedirs("photos", exist_ok=True)
        file_path = f"photos/{user_id}_{photo.file_unique_id}.jpg"
        try:
            file = await context.bot.get_file(photo.file_id)
            await file.download_to_drive(file_path)
        except OSError as exc:
            logging.exception("[PHOTO] Failed to save photo: %s", exc)
            await message.reply_text("⚠️ Не удалось сохранить фото. Попробуйте ещё раз.")
            context.user_data.pop(WAITING_GPT_FLAG, None)
            return ConversationHandler.END

    logging.info("[PHOTO] Saved to %s", file_path)

    try:
        thread_id = context.user_data.get("thread_id")
        if not thread_id:
            with SessionLocal() as session:
                user = session.get(User, user_id)
                if user:
                    thread_id = user.thread_id
                else:
                    thread_id = create_thread()
                    session.add(User(telegram_id=user_id, thread_id=thread_id))
                    if not commit_session(session):
                        await message.reply_text(
                            "⚠️ Не удалось сохранить данные пользователя."
                        )
                        return ConversationHandler.END
            context.user_data["thread_id"] = thread_id

        run = send_message(
            thread_id=thread_id,
            content=(
                "Определи **название** блюда и количество углеводов/ХЕ. Ответ:\n"
                "<название блюда>\n"
                "Углеводы: <...>\n"
                "ХЕ: <...>"
            ),
            image_path=file_path,
            keep_image=True,
        )
        status_message = await message.reply_text(
            "🔍 Анализирую фото (это займёт 5‑10 с)…"
        )
        chat_id = getattr(message, "chat_id", None)

        async def send_typing_action() -> None:
            if not chat_id:
                return
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id, action=ChatAction.TYPING
                )
            except TelegramError as exc:
                logger.warning(
                    "[PHOTO][TYPING_ACTION] Failed to send typing action: %s",
                    exc,
                )
            except Exception as exc:  # pragma: no cover - unexpected
                logger.exception(
                    "[PHOTO][TYPING_ACTION] Unexpected error: %s",
                    exc,
                )

        await send_typing_action()

        max_attempts = 15
        warn_after = 5
        for attempt in range(max_attempts):
            if run.status in ("completed", "failed", "cancelled", "expired"):
                break
            await asyncio.sleep(2)
            run = _get_client().beta.threads.runs.retrieve(
                thread_id=run.thread_id,
                run_id=run.id,
            )
            if attempt == warn_after and status_message and hasattr(
                status_message, "edit_text"
            ):
                try:
                    await status_message.edit_text("🔍 Всё ещё анализирую фото…")
                except TelegramError as exc:
                    logger.warning(
                        "[PHOTO][STATUS_EDIT] Failed to update status message: %s",
                        exc,
                    )
                except Exception as exc:  # pragma: no cover - unexpected
                    logger.exception(
                        "[PHOTO][STATUS_EDIT] Unexpected error: %s",
                        exc,
                    )
            await send_typing_action()

        if run.status not in ("completed", "failed", "cancelled", "expired"):
            logger.warning("[VISION][TIMEOUT] run.id=%s", run.id)
            if status_message and hasattr(status_message, "edit_text"):
                try:
                    await status_message.edit_text(
                        "⚠️ Время ожидания Vision истекло. Попробуйте позже."
                    )
                except TelegramError as exc:
                    logger.warning(
                        "[PHOTO][TIMEOUT_EDIT] Failed to send timeout notice: %s",
                        exc,
                    )
                except Exception as exc:  # pragma: no cover - unexpected
                    logger.exception(
                        "[PHOTO][TIMEOUT_EDIT] Unexpected error: %s",
                        exc,
                    )
            else:
                await message.reply_text(
                    "⚠️ Время ожидания Vision истекло. Попробуйте позже."
                )
            return ConversationHandler.END

        if run.status != "completed":
            logging.error("[VISION][RUN_FAILED] run.status=%s", run.status)
            if status_message and hasattr(status_message, "edit_text"):
                try:
                    await status_message.edit_text(
                        "⚠️ Vision не смог обработать фото."
                    )
                except TelegramError as exc:
                    logger.warning(
                        "[PHOTO][RUN_FAILED_EDIT] Failed to send Vision failure notice: %s",
                        exc,
                    )
                except Exception as exc:  # pragma: no cover - unexpected
                    logger.exception(
                        "[PHOTO][RUN_FAILED_EDIT] Unexpected error: %s",
                        exc,
                    )
            else:
                await message.reply_text("⚠️ Vision не смог обработать фото.")
            return ConversationHandler.END

        messages = _get_client().beta.threads.messages.list(thread_id=run.thread_id)
        for m in messages.data:
            content = _sanitize(m.content)
            logger.debug("[VISION][MSG] m.role=%s; content=%s", m.role, content)

        vision_text = next(
            (m.content[0].text.value for m in messages.data if m.role == "assistant" and m.content),
            "",
        )
        logger.debug(
            "[VISION][RESPONSE] Ответ Vision для %s:\n%s",
            file_path,
            _sanitize(vision_text),
        )

        carbs_g, xe = extract_nutrition_info(vision_text)
        if carbs_g is None and xe is None:
            logger.debug(
                "[VISION][NO_PARSE] Ответ ассистента: %r для файла: %s",
                _sanitize(vision_text),
                file_path,
            )
            await message.reply_text(
                "⚠️ Не смог разобрать углеводы на фото.\n\n"
                f"Вот полный ответ Vision:\n<pre>{vision_text}</pre>\n"
                "Введите /dose и укажите их вручную.",
                parse_mode="HTML",
                reply_markup=menu_keyboard,
            )
            return ConversationHandler.END

        pending_entry = context.user_data.get("pending_entry") or {
            "telegram_id": user_id,
            "event_time": datetime.datetime.now(datetime.timezone.utc),
        }
        pending_entry.update(
            {"carbs_g": carbs_g, "xe": xe, "photo_path": file_path}
        )
        context.user_data["pending_entry"] = pending_entry
        if status_message and hasattr(status_message, "delete"):
            try:
                await status_message.delete()
            except TelegramError as exc:
                logger.warning(
                    "[PHOTO][DELETE_STATUS] Failed to delete status message: %s",
                    exc,
                )
            except Exception as exc:  # pragma: no cover - unexpected
                logger.exception(
                    "[PHOTO][DELETE_STATUS] Unexpected error: %s",
                    exc,
                )
        await message.reply_text(
            f"🍽️ На фото:\n{vision_text}\n\n"
            "Введите текущий сахар (ммоль/л) — и я рассчитаю дозу инсулина.",
            reply_markup=menu_keyboard,
        )
        return PHOTO_SUGAR

    except OSError as exc:
        logging.exception("[PHOTO] File processing error: %s", exc)
        await message.reply_text("⚠️ Ошибка при обработке файла изображения. Попробуйте ещё раз.")
        return ConversationHandler.END
    except OpenAIError as exc:
        logging.exception("[PHOTO] Vision API error: %s", exc)
        await message.reply_text("⚠️ Vision не смог обработать фото. Попробуйте ещё раз.")
        return ConversationHandler.END
    except ValueError as exc:
        logging.exception("[PHOTO] Parsing error: %s", exc)
        await message.reply_text("⚠️ Не удалось распознать фото. Попробуйте ещё раз.")
        return ConversationHandler.END
    except TelegramError as exc:
        logging.exception("[PHOTO] Telegram error: %s", exc)
        return ConversationHandler.END
    except Exception as exc:  # pragma: no cover - unexpected
        logging.exception("[PHOTO] Unexpected error: %s", exc)
        raise
    finally:
        context.user_data.pop(WAITING_GPT_FLAG, None)


async def doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle images sent as documents."""
    document = update.message.document
    if not document:
        return ConversationHandler.END

    mime_type = document.mime_type
    if not mime_type or not mime_type.startswith("image/"):
        return ConversationHandler.END

    user_id = update.effective_user.id
    ext = Path(document.file_name).suffix or ".jpg"
    path = f"photos/{user_id}_{document.file_unique_id}{ext}"
    os.makedirs("photos", exist_ok=True)

    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(path)

    context.user_data["__file_path"] = path
    update.message.photo = []
    return await photo_handler(update, context)


prompt_photo = photo_prompt
prompt_sugar = sugar_start
prompt_dose = dose_start

sugar_conv = ConversationHandler(
    entry_points=[
        CommandHandler("sugar", sugar_start),
        MessageHandler(filters.Regex("^🩸 Уровень сахара$"), sugar_start),
    ],
    states={
        SUGAR_VAL: [
            MessageHandler(
                filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), sugar_val
            )
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex("^↩️ Назад$"), dose_cancel),
        CommandHandler("menu", _cancel_then(menu_command)),
        MessageHandler(filters.Regex("^📷 Фото еды$"), _cancel_then(photo_prompt)),
    ],
)

dose_conv = ConversationHandler(
    entry_points=[
        CommandHandler("dose", dose_start),
        MessageHandler(filters.Regex("^💉 Доза инсулина$"), dose_start),
    ],
    states={
        DOSE_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_method_choice)],
        DOSE_XE: [
            MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_xe)
        ],
        DOSE_CARBS: [
            MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_carbs)
        ],
        DOSE_SUGAR: [
            MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_sugar)
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex("^↩️ Назад$"), dose_cancel),
        CommandHandler("menu", _cancel_then(menu_command)),
        MessageHandler(filters.Regex("^📷 Фото еды$"), _cancel_then(photo_prompt)),
        MessageHandler(filters.Regex("^🩸 Уровень сахара$"), _cancel_then(sugar_start)),
        MessageHandler(filters.Regex("^📊 История$"), _cancel_then(history_view)),
        MessageHandler(filters.Regex("^📈 Отчёт$"), _cancel_then(report_request)),
        MessageHandler(filters.Regex("^📄 Мой профиль$"), _cancel_then(profile_view)),
    ],
)


__all__ = [
    "DOSE_METHOD",
    "DOSE_XE",
    "DOSE_CARBS",
    "DOSE_SUGAR",
    "PHOTO_SUGAR",
    "SUGAR_VAL",
    "WAITING_GPT_FLAG",

    "photo_prompt",
    "sugar_start",
    "sugar_val",
    "dose_start",
    "prompt_photo",
    "prompt_sugar",
    "prompt_dose",

    "sugar_conv",

    "freeform_handler",
    "photo_handler",
    "doc_handler",
    "dose_conv",
    "ConversationHandler",
]
