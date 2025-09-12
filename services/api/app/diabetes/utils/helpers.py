import logging
import os
import re
from datetime import datetime, time, timedelta
from json import JSONDecodeError
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

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
            if amount <= 0:
                raise ValueError(INVALID_TIME_MSG)
            return timedelta(hours=amount) if unit == "h" else timedelta(days=amount)
        raise ValueError(INVALID_TIME_MSG)


ALLOWED_GEO_HOSTS = {"ipinfo.io"}


async def get_coords_and_link(
    source_url: str | None = None,
) -> tuple[str | None, str | None]:
    """Return approximate coordinates and Google Maps link based on IP."""

    url = source_url or os.getenv("GEO_DATA_URL") or "https://ipinfo.io/json"

    parsed = urlparse(url)
    host = parsed.hostname.lower() if parsed.hostname else None
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
