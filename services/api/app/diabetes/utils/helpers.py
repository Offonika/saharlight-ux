import logging
import os
import re
from datetime import datetime, time, timedelta
from json import JSONDecodeError
from urllib.parse import urlparse

import httpx

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

logger = logging.getLogger(__name__)

# utils.py


def clean_markdown(text: str) -> str:
    """
    Удаляет простую Markdown-разметку: **жирный**, _курсив_, # заголовки,
    списки (*, -, +, 1. и т.д.).
    """
    replacements = [
        (r"\*\*([^*]+)\*\*", r"\1"),  # **жирный**
        (r"__([^_]+)__", r"\1"),  # __жирный__
        (r"_([^_]+)_", r"\1"),  # _курсив_
        (r"\*([^*]+)\*", r"\1"),  # *курсив*
        (r"~~([^~]+)~~", r"\1"),  # ~~зачеркнуто~~
        (r"\[([^\]]+)\]\([^\)]+\)", r"\1"),  # [текст](ссылка)
        (r"!\[([^\]]*)\]\([^\)]+\)", r"\1"),  # ![alt](ссылка)
        (r"`([^`]+)`", r"\1"),  # `код`
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # ### Заголовки
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)  # 1. списки
    text = re.sub(r"^\s*[*+-]\s*", "", text, flags=re.MULTILINE)  # bullet lists
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


ALLOWED_GEO_HOSTS = {"ipinfo.io"}
GEO_DATA_URL = os.getenv("GEO_DATA_URL", "https://ipinfo.io/json")


async def get_coords_and_link(
    source_url: str | None = None,
) -> tuple[str | None, str | None]:
    """Return approximate coordinates and Google Maps link based on IP."""

    url = source_url or GEO_DATA_URL

    parsed = urlparse(url)
    host = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or host is None
        or host not in ALLOWED_GEO_HOSTS
    ):
        logger.warning("Invalid source URL: %s", url)
        return None, None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)
            resp.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network failures
        logger.warning("Failed to fetch coordinates from %s: %s", url, exc)
        return None, None

    content_type = resp.headers.get("Content-Type", "")
    if content_type and "application/json" not in content_type.lower():
        logger.warning("Unexpected content type: %s", content_type)
        return None, None

    try:
        data = resp.json()
    except JSONDecodeError as exc:
        logger.warning("Failed to parse JSON from %s: %s", url, exc)
        return None, None

    loc = data.get("loc")
    if isinstance(loc, str):
        try:
            lat, lon = (part.strip() for part in loc.split(","))
        except ValueError:
            logger.warning("Invalid location format: %s", loc)
            return None, None
        if not lat or not lon:
            logger.warning("Invalid location format: %s", loc)
            return None, None
        coords = f"{lat},{lon}"
        link = f"https://maps.google.com/?q={lat},{lon}"
        return coords, link
    if loc is not None:
        logger.warning("Invalid location format: %s", loc)
    return None, None


def split_text_by_width(
    text: str,
    font_name: str,
    font_size: float,
    max_width_mm: float,
) -> list[str]:
    """
    Разбивает строку так, чтобы она не выходила за max_width_mm по ширине в PDF (мм).

    Raises:
        ValueError: если ``font_name`` не зарегистрирован в ReportLab или
            ``font_size``/``max_width_mm`` неположительны.
    """
    if font_size <= 0 or max_width_mm <= 0:
        raise ValueError("font_size and max_width_mm must be positive")

    words = text.split()
    lines: list[str] = []
    current_line = ""

    def _width(chunk: str) -> float:
        try:

            raw: float = float(stringWidth(chunk, font_name, font_size))
            mm_value: float = mm
            return raw / mm_value

        except KeyError as exc:
            raise ValueError(f"Unknown font '{font_name}'") from exc

    def _split_word(word: str) -> list[str]:
        """Split a single word into chunks that fit within ``max_width_mm``."""

        parts: list[str] = []
        part = ""
        for ch in word:
            test_part = part + ch

            if _width(test_part) > max_width_mm and part:

                parts.append(part)
                part = ch
            else:
                part = test_part
        if part:
            parts.append(part)
        return parts

    for word in words:
        test_line = (current_line + " " + word).strip()
        width = _width(test_line)
        if width <= max_width_mm:
            current_line = test_line
            continue

        if current_line:
            lines.append(current_line)
            current_line = ""

        if _width(word) <= max_width_mm:
            current_line = word
        else:
            parts = _split_word(word)
            lines.extend(parts[:-1])
            current_line = parts[-1] if parts else ""

    if current_line:
        lines.append(current_line)
    return lines
