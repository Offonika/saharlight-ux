"""Handlers for generating user reports."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from diabetes.db import SessionLocal, Entry
from diabetes.reporting import make_sugar_plot, generate_pdf_report

LOW_SUGAR_THRESHOLD = 3.0
HIGH_SUGAR_THRESHOLD = 13.0


async def report_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt the user for a report date and set waiting flag."""
    context.user_data["awaiting_report_date"] = True
    await update.message.reply_text(
        "Введите дату начала отчёта в формате YYYY-MM-DD",
    )


async def history_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent diary entries."""
    user_id = update.effective_user.id
    with SessionLocal() as session:
        entries = (
            session.query(Entry)
            .filter(Entry.telegram_id == user_id)
            .order_by(Entry.event_time.desc())
            .limit(10)
            .all()
        )
    if not entries:
        await update.message.reply_text("В дневнике пока нет записей.")
        return
    lines = ["📊 Последние записи:"]
    for entry in entries:
        day_str = entry.event_time.strftime("%d.%m %H:%M")
        sugar = entry.sugar_before if entry.sugar_before is not None else "—"
        carbs = entry.carbs_g if entry.carbs_g is not None else "—"
        xe = entry.xe if entry.xe is not None else "—"
        dose = entry.dose if entry.dose is not None else "—"
        lines.append(
            f"{day_str}: сахар {sugar}, углеводы {carbs} г ({xe} ХЕ), доза {dose}",
        )
    await update.message.reply_text("\n".join(lines))


async def send_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    date_from,
    period_label,
    query=None,
) -> None:
    """Generate and send a PDF report for entries after ``date_from``."""
    user_id = update.effective_user.id

    with SessionLocal() as session:
        entries = (
            session.query(Entry)
            .filter(Entry.telegram_id == user_id)
            .filter(Entry.event_time >= date_from)
            .order_by(Entry.event_time)
            .all()
        )
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

    gpt_text = "Ваши данные проанализированы. Рекомендации GPT могут быть добавлены тут."
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


__all__ = ["send_report", "report_request", "history_view"]
