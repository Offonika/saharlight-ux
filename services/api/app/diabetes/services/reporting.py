# reporting.py

import logging
import os
import io
import textwrap
import threading
from datetime import datetime
from typing import Callable, Iterable, Protocol, Sequence, cast

import matplotlib.pyplot as plt
from matplotlib.dates import date2num
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen import canvas

from services.api.app import config

logger = logging.getLogger(__name__)

date2num_typed: Callable[[datetime], float] = date2num

# Регистрация шрифтов для поддержки кириллицы и жирного начертания
DEFAULT_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
_fonts_registration_result: bool | None = None
_font_lock = threading.Lock()


class SugarEntry(Protocol):
    """Запись дневника с уровнем сахара."""

    event_time: datetime
    sugar_before: float | None


def _register_font(name: str, filename: str) -> tuple[bool, str | None]:
    settings = config.get_settings()
    font_dir = settings.font_dir or DEFAULT_FONT_DIR
    path = os.path.join(font_dir, filename)
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return True, None
    except (OSError, TTFError) as e:
        if isinstance(e, OSError):
            msg = f"[PDF] Cannot register font {name} at {path}: {e}"
        else:
            msg = f"[PDF] Invalid font {name} at {path}: {e}"
        logger.warning(msg)
        if font_dir != DEFAULT_FONT_DIR:
            fallback = os.path.join(DEFAULT_FONT_DIR, filename)
            try:
                pdfmetrics.registerFont(TTFont(name, fallback))
                return True, (
                    f"Использован запасной шрифт {fallback} для {name}: {e}"
                )
            except (OSError, TTFError) as e2:
                if isinstance(e2, OSError):
                    msg2 = f"[PDF] Failed to register default font {name} at {fallback}: {e2}"
                else:
                    msg2 = f"[PDF] Invalid default font {name} at {fallback}: {e2}"
                logger.warning(msg2)
                return False, msg2
        return False, msg


def register_fonts() -> bool:
    """Регистрация используемых шрифтов для отчётов.

    Returns:
        bool: ``True`` если все шрифты зарегистрированы и могут быть
        использованы, ``False`` если регистрация не удалась и следует
        использовать запасные встроенные шрифты.
    """

    global _fonts_registration_result
    with _font_lock:
        if _fonts_registration_result is not None:
            return _fonts_registration_result

        messages: list[str] = []
        success = True
        for name, filename in (
            ("DejaVuSans", "DejaVuSans.ttf"),
            ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
        ):
            ok, msg = _register_font(name, filename)
            if not ok:
                success = False
            if msg:
                messages.append(msg)

        if messages:
            logger.warning("[PDF] Font registration issues: %s", "; ".join(messages))

        _fonts_registration_result = success
        return success


def make_sugar_plot(entries: Iterable[SugarEntry], period_label: str) -> io.BytesIO:
    """Собирает график сахара за период.

    Args:
        entries: Итерация записей, каждая из которых имеет атрибуты
            ``event_time`` и ``sugar_before``.
        period_label: Подпись периода, выводимая в заголовке графика.

    Returns:
        BytesIO: Буфер с изображением графика в формате PNG. Если данных
        нет, в буфере будет изображение с сообщением об отсутствии данных.

    Side Effects:
        Логирует отсутствие данных и использует глобальное состояние
        ``matplotlib``.
    """
    entries_sorted = sorted(
        (e for e in entries if e.sugar_before is not None),
        key=lambda e: e.event_time,
    )
    times: list[float] = [date2num_typed(e.event_time) for e in entries_sorted]
    sugars_plot: list[float] = [cast(float, e.sugar_before) for e in entries_sorted]

    if not sugars_plot:
        logger.info("No sugar data available for %s", period_label)
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
    plt.plot(times, sugars_plot, marker="o", label="Сахар (ммоль/л)")
    plt.gca().xaxis_date()
    plt.gcf().autofmt_xdate()
    plt.title(f"Динамика сахара за {period_label}")
    plt.xlabel("Дата")
    plt.ylabel("Сахар, ммоль/л")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf


def wrap_text(text: str, width: int = 100) -> list[str]:
    """Переносит строки по длине для PDF.

    Args:
        text: Исходная строка.
        width: Максимальная длина строки. По умолчанию 100 символов.

    Returns:
        list[str]: Список строк с учётом переноса.

    Side Effects:
        Нет.
    """
    lines: list[str] = []
    for line in text.splitlines():
        lines += textwrap.wrap(line, width=width) or [""]
    return lines


def generate_pdf_report(
    summary_lines: Sequence[str],
    errors: Sequence[str],
    day_lines: Sequence[str],
    gpt_text: str,
    plot_buf: io.BytesIO | None,
) -> io.BytesIO:
    """Генерирует PDF-отчёт для врача.

    Args:
        summary_lines: Сводка по записей дневника.
        errors: Список ошибок или критических значений.
        day_lines: Динамика показателей по дням.
        gpt_text: Текст рекомендаций.
        plot_buf: Буфер с графиком в формате PNG, либо ``None``.

    Returns:
        BytesIO: Буфер с готовым PDF-отчётом.

    Side Effects:
        Использует библиотеку ``reportlab`` для записи PDF и может
        логировать предупреждения при ошибках чтения изображения.
    """
    fonts_available = register_fonts()
    if fonts_available:
        regular_font = "DejaVuSans"
        bold_font = "DejaVuSans-Bold"
    else:
        regular_font = "Helvetica"
        bold_font = "Helvetica-Bold"

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    def check_page_break(y_pos: float, font_name: str, font_size: int) -> float:
        if y_pos < 25 * mm:
            c.showPage()
            y_pos = height - 25 * mm
            c.setFont(font_name, font_size)
        return y_pos

    x_margin = 20 * mm
    y = height - 30 * mm

    # Заголовок
    c.setFont(bold_font, 18)
    c.drawString(x_margin, y, "Отчёт по дневнику диабета")
    y -= 12 * mm

    # Summary
    c.setFont(bold_font, 13)
    y = check_page_break(y, bold_font, 13)
    c.drawString(x_margin, y, "Сводка:")
    y -= 7 * mm
    c.setFont(regular_font, 11)
    y = check_page_break(y, regular_font, 11)
    for line in summary_lines:
        c.drawString(x_margin, y, line)
        y -= 6 * mm
        y = check_page_break(y, regular_font, 11)

    if errors:
        c.setFont(bold_font, 13)
        y = check_page_break(y, bold_font, 13)
        c.drawString(x_margin, y, "Ошибки и критические значения:")
        y -= 7 * mm
        c.setFont(regular_font, 11)
        y = check_page_break(y, regular_font, 11)
        for err in errors:
            c.drawString(x_margin, y, err)
            y -= 6 * mm
            y = check_page_break(y, regular_font, 11)

    if day_lines:
        c.setFont(bold_font, 13)
        y = check_page_break(y, bold_font, 13)
        c.drawString(x_margin, y, "Динамика по дням:")
        y -= 7 * mm
        c.setFont(regular_font, 11)
        y = check_page_break(y, regular_font, 11)
        for line in day_lines:
            c.drawString(x_margin, y, line)
            y -= 6 * mm
            y = check_page_break(y, regular_font, 11)

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
        except OSError as e:
            logger.warning("[PDF] Cannot read plot image: %s", e)
        except ValueError as e:
            logger.exception("[PDF] Invalid plot image: %s", e)

    # Анализ и рекомендации
    y -= 8 * mm
    c.setFont(bold_font, 13)
    c.drawString(x_margin, y, "Анализ и рекомендации:")
    y -= 7 * mm
    c.setFont(regular_font, 11)
    for line in wrap_text(gpt_text, width=100):
        c.drawString(x_margin, y, line)
        y -= 6 * mm
        y = check_page_break(y, regular_font, 11)
    c.save()
    buffer.seek(0)
    return buffer
