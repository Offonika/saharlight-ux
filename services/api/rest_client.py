from __future__ import annotations

from typing import cast

import httpx

from .app.config import get_settings


async def get_json(path: str) -> dict[str, object]:
    base = get_settings().api_url
    if not base:
        raise RuntimeError("API_URL not configured")
    url = f"{base.rstrip('/')}{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return cast(dict[str, object], resp.json())
