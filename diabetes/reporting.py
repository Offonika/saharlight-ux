# reporting.py

import matplotlib.pyplot as plt
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
import textwrap

# Регистрация шрифтов для поддержки кириллицы и жирного начертания
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

def make_sugar_plot(entries, period_label):
    """
    Генерирует график сахара за период. Возвращает BytesIO с PNG.
    """
    times = [e.event_time for e in entries if e.sugar_before is not None]
    sugars_plot = [e.sugar_before for e in entries if e.sugar_before is not None]

    plt.figure(figsize=(7, 3))
    plt.plot(times, sugars_plot, marker='o', label='Сахар (ммоль/л)')
    plt.title(f'Динамика сахара за {period_label}')
    plt.xlabel('Дата')
    plt.ylabel('Сахар, ммоль/л')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def wrap_text(text, width=100):
    """
    Переносит строки по длине для PDF.
    """
    lines = []
    for line in text.splitlines():
        lines += textwrap.wrap(line, width=width) or [""]
    return lines

def generate_pdf_report(summary_lines, errors, day_lines, gpt_text, plot_buf):
    """
    Генерирует PDF-отчёт для врача с графиком и рекомендациями.
    Возвращает BytesIO с PDF.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x_margin = 20 * mm
    y = height - 30 * mm

    # Заголовок
    c.setFont("DejaVuSans-Bold", 18)
    c.drawString(x_margin, y, "Отчёт по дневнику диабета")
    y -= 12 * mm

    # Summary
    c.setFont("DejaVuSans-Bold", 13)
    c.drawString(x_margin, y, "Сводка:")
    y -= 7 * mm
    c.setFont("DejaVuSans", 11)
    for line in summary_lines:
        c.drawString(x_margin, y, line)
        y -= 6 * mm

    if errors:
        c.setFont("DejaVuSans-Bold", 13)
        c.drawString(x_margin, y, "Ошибки и критические значения:")
        y -= 7 * mm
        c.setFont("DejaVuSans", 11)
        for err in errors:
            c.drawString(x_margin, y, err)
            y -= 6 * mm

    if day_lines:
        c.setFont("DejaVuSans-Bold", 13)
        c.drawString(x_margin, y, "Динамика по дням:")
        y -= 7 * mm
        c.setFont("DejaVuSans", 11)
        for line in day_lines:
            c.drawString(x_margin, y, line)
            y -= 6 * mm

    # Вставка графика
    if plot_buf:
        try:
            y -= 10 * mm
            img_reader = None
            plot_buf.seek(0)
            img_reader = io.BytesIO(plot_buf.read())
            c.drawImage(img_reader, x_margin, y - 65*mm, width=160*mm, height=55*mm, preserveAspectRatio=True)
            y -= 65 * mm
        except Exception as e:
            pass

    # Анализ и рекомендации
    y -= 8 * mm
    c.setFont("DejaVuSans-Bold", 13)
    c.drawString(x_margin, y, "Анализ и рекомендации:")
    y -= 7 * mm
    c.setFont("DejaVuSans", 11)
    for line in wrap_text(gpt_text, width=100):
        c.drawString(x_margin, y, line)
        y -= 6 * mm
        if y < 25 * mm:
            c.showPage()
            y = height - 25 * mm
            c.setFont("DejaVuSans", 11)
    c.save()
    buffer.seek(0)
    return buffer
