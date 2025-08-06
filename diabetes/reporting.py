# reporting.py

import os
import io
import logging
import textwrap

import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from diabetes.config import FONT_DIR

# Регистрация шрифтов для поддержки кириллицы и жирного начертания
DEFAULT_FONT_DIR = '/usr/share/fonts/truetype/dejavu'
_font_dir = FONT_DIR or DEFAULT_FONT_DIR


def _register_font(name, filename):
    path = os.path.join(_font_dir, filename)
    try:
        pdfmetrics.registerFont(TTFont(name, path))
    except Exception as e:
        logging.warning("[PDF] Cannot register font %s at %s: %s", name, path, e)
        if _font_dir != DEFAULT_FONT_DIR:
            fallback = os.path.join(DEFAULT_FONT_DIR, filename)
            try:
                pdfmetrics.registerFont(TTFont(name, fallback))
            except Exception as e2:
                logging.exception(
                    "[PDF] Failed to register default font %s at %s: %s",
                    name,
                    fallback,
                    e2,
                )


_register_font('DejaVuSans', 'DejaVuSans.ttf')
_register_font('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf')


def make_sugar_plot(entries, period_label):
    """
    Генерирует график сахара за период. Возвращает BytesIO с PNG.
    Если данных нет, возвращает изображение с сообщением об отсутствии данных.
    """
    times = [e.event_time for e in entries if e.sugar_before is not None]
    sugars_plot = [e.sugar_before for e in entries if e.sugar_before is not None]

    if not sugars_plot:
        logging.info("No sugar data available for %s", period_label)
        buf = io.BytesIO()
        plt.figure(figsize=(7, 3))
        plt.text(
            0.5,
            0.5,
            "Нет данных для построения графика",
            ha="center",
            va="center",
        )
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()
        return buf

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

    def check_page_break(y_pos, font_name, font_size):
        if y_pos < 25 * mm:
            c.showPage()
            y_pos = height - 25 * mm
            c.setFont(font_name, font_size)
        return y_pos

    x_margin = 20 * mm
    y = height - 30 * mm

    # Заголовок
    c.setFont("DejaVuSans-Bold", 18)
    c.drawString(x_margin, y, "Отчёт по дневнику диабета")
    y -= 12 * mm

    # Summary
    c.setFont("DejaVuSans-Bold", 13)
    y = check_page_break(y, "DejaVuSans-Bold", 13)
    c.drawString(x_margin, y, "Сводка:")
    y -= 7 * mm
    c.setFont("DejaVuSans", 11)
    y = check_page_break(y, "DejaVuSans", 11)
    for line in summary_lines:
        c.drawString(x_margin, y, line)
        y -= 6 * mm
        y = check_page_break(y, "DejaVuSans", 11)

    if errors:
        c.setFont("DejaVuSans-Bold", 13)
        y = check_page_break(y, "DejaVuSans-Bold", 13)
        c.drawString(x_margin, y, "Ошибки и критические значения:")
        y -= 7 * mm
        c.setFont("DejaVuSans", 11)
        y = check_page_break(y, "DejaVuSans", 11)
        for err in errors:
            c.drawString(x_margin, y, err)
            y -= 6 * mm
            y = check_page_break(y, "DejaVuSans", 11)

    if day_lines:
        c.setFont("DejaVuSans-Bold", 13)
        y = check_page_break(y, "DejaVuSans-Bold", 13)
        c.drawString(x_margin, y, "Динамика по дням:")
        y -= 7 * mm
        c.setFont("DejaVuSans", 11)
        y = check_page_break(y, "DejaVuSans", 11)
        for line in day_lines:
            c.drawString(x_margin, y, line)
            y -= 6 * mm
            y = check_page_break(y, "DejaVuSans", 11)

    # Вставка графика
    if plot_buf:
        try:
            y -= 10 * mm
            plot_buf.seek(0)
            img_reader = ImageReader(plot_buf)
            c.drawImage(
                img_reader,
                x_margin,
                y - 65 * mm,
                width=160 * mm,
                height=55 * mm,
                preserveAspectRatio=True,
            )
            y -= 65 * mm
        except Exception as e:
            logging.exception("[PDF] Failed to draw plot image: %s", e)

    # Анализ и рекомендации
    y -= 8 * mm
    c.setFont("DejaVuSans-Bold", 13)
    c.drawString(x_margin, y, "Анализ и рекомендации:")
    y -= 7 * mm
    c.setFont("DejaVuSans", 11)
    for line in wrap_text(gpt_text, width=100):
        c.drawString(x_margin, y, line)
        y -= 6 * mm
        y = check_page_break(y, "DejaVuSans", 11)
    c.save()
    buffer.seek(0)
    return buffer
