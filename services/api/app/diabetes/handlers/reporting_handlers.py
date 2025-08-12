"""Handlers for generating user reports."""

from __future__ import annotations

import asyncio
import datetime
import html
import logging

from openai import OpenAIError
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from services.api.app.diabetes.services.db import SessionLocal, Entry, User
from services.api.app.diabetes.services.gpt_client import (
    send_message,
    _get_client,
    create_thread,
)
from .common_handlers import commit_session
from services.api.app.diabetes.services.reporting import make_sugar_plot, generate_pdf_report
from services.api.app.diabetes.utils.ui import menu_keyboard

LOW_SUGAR_THRESHOLD = 3.0
HIGH_SUGAR_THRESHOLD = 13.0


def render_entry(entry: Entry) -> str:
    """Render a single diary entry as HTML-formatted text."""
    day_str = html.escape(entry.event_time.strftime("%d.%m %H:%M"))
    sugar = (
        html.escape(str(entry.sugar_before))
        if entry.sugar_before is not None
        else "—"
    )
    dose = (
        html.escape(str(entry.dose)) if entry.dose is not None else "—"
    )

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
            InlineKeyboardButton(
                "Сегодня", callback_data="report_period:today"
            ),
            InlineKeyboardButton(
                "Неделя", callback_data="report_period:week"
            ),
        ],
        [
            InlineKeyboardButton(
                "Месяц", callback_data="report_period:month"
            ),
            InlineKeyboardButton(
                "Произвольно", callback_data="report_period:custom"
            ),
        ],
        [InlineKeyboardButton("↩️ Назад", callback_data="report_back")],
    ]
    return InlineKeyboardMarkup(rows)


async def report_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt the user to select a report period."""
    await update.message.reply_text(
        "Выберите период отчёта:", reply_markup=report_keyboard()
    )


async def history_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent diary entries as separate messages with action buttons."""
    user_id = update.effective_user.id

    def _fetch_entries() -> list[Entry]:
        with SessionLocal() as session:
            return (
                session.query(Entry)
                .filter(Entry.telegram_id == user_id)
                .order_by(Entry.event_time.desc())
                .limit(10)
                .all()
            )

    # Run DB work in a thread to keep the event loop responsive.
    entries = await asyncio.to_thread(_fetch_entries)
    if not entries:
        await update.message.reply_text("В дневнике пока нет записей.")
        return

    await update.message.reply_text("📊 Последние записи:")
    for entry in entries:
        text = render_entry(entry)
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✏️ Изменить", callback_data=f"edit:{entry.id}"
                    ),
                    InlineKeyboardButton(
                        "🗑 Удалить", callback_data=f"del:{entry.id}"
                    ),
                ]
            ]
        )
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=markup
        )

    back_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Назад", callback_data="report_back")]]
    )
    await update.message.reply_text("Готово.", reply_markup=back_markup)


async def report_period_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle report period selection via inline buttons."""
    query = update.callback_query
    await query.answer()
    if query.data == "report_back":
        await query.message.delete()
        await query.message.reply_text(
            "📋 Выберите действие:", reply_markup=menu_keyboard
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
        context.user_data["awaiting_report_date"] = True
        await query.edit_message_text(
            "Введите дату начала отчёта в формате YYYY-MM-DD\n"
            "Отправьте «назад» для отмены."
        )
        if getattr(query, "message", None):
            await query.message.reply_text(
                "Ожидаю дату…",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("↩️ Назад")]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                ),
            )
    else:  # pragma: no cover - defensive
        await query.edit_message_text("Команда не распознана")


async def send_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    date_from,
    period_label,
    query=None,
) -> None:
    """Generate and send a PDF report for entries after ``date_from``."""
    user_id = update.effective_user.id

    def _fetch_entries() -> list[Entry]:
        with SessionLocal() as session:
            return (
                session.query(Entry)
                .filter(Entry.telegram_id == user_id)
                .filter(Entry.event_time >= date_from)
                .order_by(Entry.event_time)
                .all()
            )

    # Run blocking DB calls in a thread to avoid freezing the event loop.
    entries = await asyncio.to_thread(_fetch_entries)
    if not entries:
        text = f"Нет записей за {period_label}."
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

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
    gpt_text = default_gpt_text
    thread_id = context.user_data.get("thread_id")
    if thread_id is None:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            thread_id = getattr(user, "thread_id", None)
            if thread_id is None:
                thread_id = create_thread()
                if user:
                    user.thread_id = thread_id
                else:
                    session.add(User(telegram_id=user_id, thread_id=thread_id))
                if commit_session(session):
                    context.user_data["thread_id"] = thread_id
                else:
                    thread_id = None
            else:
                context.user_data["thread_id"] = thread_id
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
                        m.content[0].text.value
                        for m in messages.data
                        if m.role == "assistant" and m.content
                    ),
                    default_gpt_text,
                )
            else:
                logging.error("[GPT][RUN_FAILED] status=%s", run.status)
        except OpenAIError:
            logging.exception("[GPT] Failed to get recommendations")
        except OSError as exc:
            logging.exception(
                "[GPT] OS error while getting recommendations: %s", exc
            )
    else:
        logging.warning("[GPT] thread_id missing for user %s", user_id)
    report_msg = "<b>Отчёт сформирован</b>\n\n" + "\n".join(summary_lines + day_lines)

    plot_buf = make_sugar_plot(entries, period_label)
    pdf_buf = generate_pdf_report(summary_lines, errors, day_lines, gpt_text, plot_buf)
    plot_buf.seek(0)
    pdf_buf.seek(0)
    if query:
        await query.edit_message_text(report_msg, parse_mode="HTML")
        await query.message.reply_photo(
            plot_buf,
            caption="График сахара за период",
        )
        await query.message.reply_document(
            pdf_buf,
            filename="diabetes_report.pdf",
            caption="PDF-отчёт для врача",
        )
    else:
        await update.message.reply_text(report_msg, parse_mode="HTML")
        await update.message.reply_photo(
            plot_buf,
            caption="График сахара за период",
        )
        await update.message.reply_document(
            pdf_buf,
            filename="diabetes_report.pdf",
            caption="PDF-отчёт для врача",
        )


__all__ = [
    "send_report",
    "report_request",
    "history_view",
    "report_keyboard",
    "report_period_callback",
]
