# utils.py

import asyncio
import json
import logging
import re
from datetime import datetime, time, timedelta
from urllib.request import urlopen

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm


def clean_markdown(text: str) -> str:
    """
    Удаляет простую Markdown-разметку: **жирный**, # заголовки, * списки, 1. списки и т.д.
    """
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **жирный**
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)  # ### Заголовки
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)  # 1. списки
    text = re.sub(r'^\s*\*\s*', '', text, flags=re.MULTILINE)      # * списки
    text = re.sub(r'`([^`]+)`', r'\1', text)           # `код`
    return text


INVALID_TIME_MSG = "❌ Неверный формат. Примеры: 22:30 | 6:00 | 5h | 3d"


def parse_time_interval(value: str) -> time | timedelta:
    """Convert strings like 'HH:MM', 'H:MM', 'Nh' or 'Nd' to time or timedelta."""

    value = value.strip()
    # Normalize times like `9:30` -> `09:30` before parsing
    if re.match(r"^\d:\d{2}$", value):
        value = f"0{value}"
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        match = re.fullmatch(r"(\d+)([hd])", value, re.IGNORECASE)
        if match:
            num, unit = match.groups()
            unit = unit.lower()
            amount = int(num)
            return timedelta(hours=amount) if unit == "h" else timedelta(days=amount)
        raise ValueError(INVALID_TIME_MSG)


async def get_coords_and_link() -> tuple[str | None, str | None]:
    """Return approximate coordinates and Google Maps link based on IP."""

    def _fetch() -> tuple[str | None, str | None]:
        with urlopen("https://ipinfo.io/json", timeout=5) as resp:
            data = json.load(resp)
            loc = data.get("loc")
            if loc:
                try:
                    lat, lon = loc.split(",")
                except ValueError:
                    logging.warning("Invalid location format: %s", loc)
                    return None, None
                coords = f"{lat},{lon}"
                link = f"https://maps.google.com/?q={lat},{lon}"
                return coords, link
        return None, None

    try:
        result = await asyncio.to_thread(_fetch)
        if result:
            return result
    except Exception as exc:  # pragma: no cover - network failures
        logging.warning("Failed to fetch coordinates: %s", exc)
    return "0.0,0.0", "https://maps.google.com/?q=0.0,0.0"


def split_text_by_width(
    text: str,
    font_name: str,
    font_size: float,
    max_width_mm: float,
) -> list[str]:
    """
    Разбивает строку так, чтобы она не выходила за max_width_mm по ширине в PDF (мм).
    """
    words = text.split()
    lines: list[str] = []
    current_line = ""
    for word in words:
        test_line = (current_line + " " + word).strip()
        width = stringWidth(test_line, font_name, font_size) / mm
        if width > max_width_mm and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines
