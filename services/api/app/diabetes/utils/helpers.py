import asyncio
import json
import logging
import os
import re
from datetime import datetime, time, timedelta
from json import JSONDecodeError
from urllib.error import URLError
from urllib.request import urlopen

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

logger = logging.getLogger(__name__)

# utils.py


def clean_markdown(text: str) -> str:
    """
    Удаляет простую Markdown-разметку: **жирный**, # заголовки, * списки, 1. списки и т.д.
    """
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # **жирный**
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # ### Заголовки
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)  # 1. списки
    text = re.sub(r"^\s*\*\s*", "", text, flags=re.MULTILINE)  # * списки
    text = re.sub(r"`([^`]+)`", r"\1", text)  # `код`
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


GEO_DATA_URL = os.getenv("GEO_DATA_URL", "https://ipinfo.io/json")


async def get_coords_and_link(
    source_url: str | None = None,
) -> tuple[str | None, str | None]:
    """Return approximate coordinates and Google Maps link based on IP."""

    url = source_url or GEO_DATA_URL

    def _fetch() -> tuple[str | None, str | None]:
        with urlopen(url, timeout=5) as resp:
            status = getattr(resp, "getcode", lambda: 200)()
            if status != 200:
                logger.warning("Unexpected response code: %s", status)
                return None, None
            content_type = ""
            if hasattr(resp, "headers"):
                content_type = resp.headers.get("Content-Type", "")
            elif hasattr(resp, "info"):
                # ``info()`` returns mapping-like headers for ``urllib`` responses.
                content_type = resp.info().get("Content-Type", "")
            if content_type and "application/json" not in content_type:
                logger.warning("Unexpected content type: %s", content_type)
                return None, None
            data = json.load(resp)
            loc = data.get("loc")
            if loc:
                try:
                    lat, lon = loc.split(",")
                except ValueError:
                    logger.warning("Invalid location format: %s", loc)
                    return None, None
                coords = f"{lat},{lon}"
                link = f"https://maps.google.com/?q={lat},{lon}"
                return coords, link
        return None, None

    try:
        return await asyncio.to_thread(_fetch)
    except (URLError, JSONDecodeError, TimeoutError, OSError) as exc:  # pragma: no cover - network failures
        logger.warning("Failed to fetch coordinates from %s: %s", url, exc)
        return None, None


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

    def _split_word(word: str) -> list[str]:
        """Split a single word into chunks that fit within ``max_width_mm``."""

        parts: list[str] = []
        part = ""
        for ch in word:
            test_part = part + ch
            if stringWidth(test_part, font_name, font_size) / mm > max_width_mm and part:
                parts.append(part)
                part = ch
            else:
                part = test_part
        if part:
            parts.append(part)
        return parts

    for word in words:
        test_line = (current_line + " " + word).strip()
        width = stringWidth(test_line, font_name, font_size) / mm
        if width <= max_width_mm:
            current_line = test_line
            continue

        if current_line:
            lines.append(current_line)
            current_line = ""

        if stringWidth(word, font_name, font_size) / mm <= max_width_mm:
            current_line = word
        else:
            parts = _split_word(word)
            lines.extend(parts[:-1])
            current_line = parts[-1] if parts else ""

    if current_line:
        lines.append(current_line)
    return lines
