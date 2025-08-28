"""Handlers for generating user reports."""

from __future__ import annotations

import asyncio
import datetime  # Re-export for tests and type checkers
import html
import logging
import os  # Re-export for tests and type checkers

from dataclasses import dataclass
from typing import Protocol, cast

from openai import OpenAIError
from openai.types.beta.threads import TextContentBlock
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ContextTypes

from services.api.app.diabetes.services.db import SessionLocal, HistoryRecord, User
from services.api.app.diabetes.services.gpt_client import (
    send_message,
    _get_client,
    create_thread,
)
from services.api.app.diabetes.services.repository import CommitError, commit
from services.api.app.diabetes.services.reporting import (
    make_sugar_plot,
    generate_pdf_report,
)
from sqlalchemy import and_, or_
from services.api.app.diabetes.utils.ui import menu_keyboard, BACK_BUTTON_TEXT
from . import UserData

logger = logging.getLogger(__name__)

LOW_SUGAR_THRESHOLD = 3.0
HIGH_SUGAR_THRESHOLD = 13.0


class EntryLike(Protocol):
    """Protocol describing the fields required for ``render_entry``."""

    event_time: datetime.datetime
    sugar_before: float | None
    carbs_g: float | None
    xe: float | None
    dose: float | str | None


@dataclass
class HistoryEntry:
    """Adapter converting ``HistoryRecord`` fields to ``EntryLike``."""

    event_time: datetime.datetime
    sugar_before: float | None
    carbs_g: float | None
    xe: float | None
    dose: float | str | None


def _adapt_history_record(record: HistoryRecord) -> HistoryEntry:
    return HistoryEntry(
        event_time=datetime.datetime.combine(record.date, record.time),
        sugar_before=record.sugar,
        carbs_g=record.carbs,
        xe=record.bread_units,
        dose=record.insulin,
    )


def render_entry(entry: EntryLike) -> str:
    """Render a single diary entry as HTML-formatted text."""
    day_str = html.escape(entry.event_time.strftime("%d.%m %H:%M"))
    sugar = (
        html.escape(str(entry.sugar_before)) if entry.sugar_before is not None else "—"
    )
    dose = html.escape(str(entry.dose)) if entry.dose is not None else "—"

    if entry.carbs_g is not None:
        carbs_text = f"{html.escape(str(entry.carbs_g))} г"
        if entry.xe is not None:
            carbs_text += f" ({html.escape(str(entry.xe))} ХЕ)"
    elif entry.xe is not None:
        carbs_text = f"{html.escape(str(entry.xe))} ХЕ"
    else:
        carbs_text = "—"

    return (
        f"<b>{day_str}</b>\n"
        f"🍭 Сахар: <b>{sugar}</b>\n"
        f"🍞 Углеводы: <b>{carbs_text}</b>\n"
        f"💉 Доза: <b>{dose}</b>"
    )


def report_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting report period."""
    rows = [
        [
            InlineKeyboardButton("Сегодня", callback_data="report_period:today"),
            InlineKeyboardButton("Неделя", callback_data="report_period:week"),
        ],
        [
            InlineKeyboardButton("Месяц", callback_data="report_period:month"),
            InlineKeyboardButton("Произвольно", callback_data="report_period:custom"),
        ],
        [InlineKeyboardButton(BACK_BUTTON_TEXT, callback_data="report_back")],
    ]
    return InlineKeyboardMarkup(rows)


async def report_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt the user to select a report period."""
    message = update.message
    if message is None:
        return
    await message.reply_text("Выберите период отчёта:", reply_markup=report_keyboard())


async def history_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent diary entries as separate messages with action buttons."""
    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    user_id = user.id

    def _fetch_entries() -> list[HistoryRecord]:
        with SessionLocal() as session:
            return (
                session.query(HistoryRecord)
                .filter(HistoryRecord.telegram_id == user_id)
                .order_by(HistoryRecord.date.desc(), HistoryRecord.time.desc())
                .limit(10)
                .all()
            )

    # Run DB work in a thread to keep the event loop responsive.
    records = await asyncio.to_thread(_fetch_entries)
    if not records:
        await message.reply_text("В дневнике пока нет записей.")
        return

    await message.reply_text("📊 Последние записи:")

    from services.api.app import config

    settings = config.get_settings()
    if settings.public_origin:
        open_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🌐 Открыть историю в WebApp",
                        web_app=WebAppInfo(config.build_ui_url("/history")),
                    )
                ]
            ]
        )
        await message.reply_text(
            "История также доступна в WebApp:", reply_markup=open_markup
        )

    for record in records:
        text = render_entry(_adapt_history_record(record))
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✏️ Изменить", callback_data=f"edit:{record.id}"
                    ),
                    InlineKeyboardButton("🗑 Удалить", callback_data=f"del:{record.id}"),
                ]
            ]
        )
        await message.reply_text(text, parse_mode="HTML", reply_markup=markup)

    back_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Назад", callback_data="report_back")]]
    )
    await message.reply_text("Готово.", reply_markup=back_markup)


async def report_period_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle report period selection via inline buttons."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    message = query.message
    if query.data == "report_back":
        if message is not None:
            await message.delete()
            await message.reply_text(
                "📋 Выберите действие:", reply_markup=menu_keyboard()
            )
        return
    period = query.data.split(":", 1)[1]
    now = datetime.datetime.now(datetime.timezone.utc)
    if period == "today":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        await send_report(update, context, date_from, "сегодня", query=query)
    elif period == "week":
        date_from = (now - datetime.timedelta(days=7)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        await send_report(update, context, date_from, "последнюю неделю", query=query)
    elif period == "month":
        date_from = (now - datetime.timedelta(days=30)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        await send_report(update, context, date_from, "последний месяц", query=query)
    elif period == "custom":
        user_data_raw = context.user_data
        if user_data_raw is None:
            context.user_data = {}
            user_data_raw = context.user_data
        assert user_data_raw is not None
        user_data = cast(UserData, user_data_raw)
        user_data["awaiting_report_date"] = True
        await query.edit_message_text(
            "Введите дату начала отчёта в формате YYYY-MM-DD\n"
            "Отправьте «назад» для отмены."
        )
        if message is not None:
            await message.reply_text(
                "Ожидаю дату…",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton(BACK_BUTTON_TEXT)]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                ),
            )
    else:  # pragma: no cover - defensive
        await query.edit_message_text("Команда не распознана")


async def send_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    date_from: datetime.datetime,
    period_label: str,
    query: CallbackQuery | None = None,
) -> None:
    """Generate and send a PDF report for entries after ``date_from``."""
    tg_user = update.effective_user
    if tg_user is None:
        return
    user_id = tg_user.id
    message = update.message

    def _fetch_entries() -> list[HistoryRecord]:
        with SessionLocal() as session:
            date_part = date_from.date()
            time_part = date_from.time()
            return (
                session.query(HistoryRecord)
                .filter(
                    HistoryRecord.telegram_id == user_id,
                    or_(
                        HistoryRecord.date > date_part,
                        and_(
                            HistoryRecord.date == date_part,
                            HistoryRecord.time >= time_part,
                        ),
                    ),
                )
                .order_by(HistoryRecord.date, HistoryRecord.time)
                .all()
            )

    # Run blocking DB calls in a thread to avoid freezing the event loop.
    records = await asyncio.to_thread(_fetch_entries)
    if not records:
        text = f"Нет записей за {period_label}."
        if query is not None:
            await query.edit_message_text(text)
        elif message is not None:
            await message.reply_text(text)
        return

    entries = [_adapt_history_record(r) for r in records]

    summary_lines = [f"Всего записей: {len(entries)}"]
    errors = []
    day_lines = []
    for entry in entries:
        day_str = entry.event_time.strftime("%d.%m")
        sugar = entry.sugar_before if entry.sugar_before is not None else "—"
        carbs = entry.carbs_g if entry.carbs_g is not None else "—"
        dose = entry.dose if entry.dose is not None else "—"
        line = f"{day_str}: сахар {sugar}, углеводы {carbs}, доза {dose}"
        day_lines.append(line)
        if entry.sugar_before is not None:
            if entry.sugar_before < LOW_SUGAR_THRESHOLD:
                errors.append(f"{day_str}: низкий сахар {entry.sugar_before}")
            elif entry.sugar_before > HIGH_SUGAR_THRESHOLD:
                errors.append(f"{day_str}: высокий сахар {entry.sugar_before}")
    summary_text = "\n".join(summary_lines)
    errors_text = "\n".join(errors) if errors else "нет"
    days_text = "\n".join(day_lines)

    prompt = (
        "Проанализируй дневник диабета пользователя и предложи краткие рекомендации."
        "\n\nСводка:\n{summary}\n\nОшибки и критические значения:\n{errors}"
        "\n\nДанные по дням:\n{days}\n"
    ).format(summary=summary_text, errors=errors_text, days=days_text)

    default_gpt_text = "Не удалось получить рекомендации."
    gpt_text: str | None = default_gpt_text
    user_data_raw = context.user_data
    if user_data_raw is None:
        context.user_data = {}
        user_data_raw = context.user_data
    assert user_data_raw is not None
    user_data = cast(UserData, user_data_raw)
    thread_id = cast(str | None, user_data.get("thread_id"))
    if thread_id is None:
        with SessionLocal() as session:
            db_user = session.get(User, user_id)
            thread_id = getattr(db_user, "thread_id", None)
            if thread_id is None:
                thread_id = await create_thread()
                if db_user:
                    db_user.thread_id = thread_id
                else:
                    session.add(User(telegram_id=user_id, thread_id=thread_id))
                try:
                    commit(session)
                except CommitError:
                    thread_id = None
                else:
                    user_data["thread_id"] = thread_id
            else:
                user_data["thread_id"] = thread_id
    if thread_id:
        try:
            run = await send_message(thread_id=thread_id, content=prompt)
            max_attempts = 15
            for _ in range(max_attempts):
                if run.status in ("completed", "failed", "cancelled", "expired"):
                    break
                await asyncio.sleep(2)
                run = await asyncio.to_thread(
                    _get_client().beta.threads.runs.retrieve,
                    thread_id=run.thread_id,
                    run_id=run.id,
                )
            if run.status == "completed":
                messages = await asyncio.to_thread(
                    _get_client().beta.threads.messages.list,
                    thread_id=run.thread_id,
                )
                gpt_text = next(
                    (
                        block.text.value
                        for m in messages.data
                        if m.role == "assistant"
                        for block in m.content
                        if isinstance(block, TextContentBlock)
                    ),
                    None,
                )
                if gpt_text is None:
                    gpt_text = next(
                        (
                            block.text.value
                            for m in messages.data
                            if m.role == "assistant"
                            for block in m.content
                            if hasattr(block, "text") and hasattr(block.text, "value")
                        ),
                        default_gpt_text,
                    )
            else:
                logger.error("[GPT][RUN_FAILED] status=%s", run.status)
        except OpenAIError:
            logger.exception("[GPT] Failed to get recommendations")
        except OSError as exc:
            logger.exception("[GPT] OS error while getting recommendations: %s", exc)
    else:
        logger.warning("[GPT] thread_id missing for user %s", user_id)
    report_msg = "<b>Отчёт сформирован</b>\n\n" + "\n".join(summary_lines + day_lines)

    plot_buf = make_sugar_plot(entries, period_label)
    pdf_buf = generate_pdf_report(
        summary_lines, errors, day_lines, gpt_text or default_gpt_text, plot_buf
    )
    plot_buf.seek(0)
    pdf_buf.seek(0)
    if query is not None:
        await query.edit_message_text(report_msg, parse_mode="HTML")
        q_message = query.message
        if q_message is None:
            return
        await q_message.reply_photo(
            plot_buf,
            caption="График сахара за период",
        )
        await q_message.reply_document(
            pdf_buf,
            filename="diabetes_report.pdf",
            caption="PDF-отчёт для врача",
        )
    elif message is not None:
        msg = message
        await msg.reply_text(report_msg, parse_mode="HTML")
        await msg.reply_photo(
            plot_buf,
            caption="График сахара за период",
        )
        await msg.reply_document(
            pdf_buf,
            filename="diabetes_report.pdf",
            caption="PDF-отчёт для врача",
        )


__all__ = [
    "datetime",
    "os",
    "send_report",
    "report_request",
    "history_view",
    "report_keyboard",
    "report_period_callback",
]
