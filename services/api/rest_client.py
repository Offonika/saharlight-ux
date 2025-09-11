from __future__ import annotations

from typing import cast

import httpx
from telegram.ext import ContextTypes

from .app.config import get_settings


class AuthRequiredError(RuntimeError):
    """Raised when user authorization is required but missing."""

    MESSAGE = (
        "\U0001f512 Требуется авторизация. Откройте приложение заново через кнопку /start."
    )

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


async def get_json(
    path: str, ctx: ContextTypes.DEFAULT_TYPE | None = None
) -> dict[str, object]:
    base_settings = get_settings()
    base = base_settings.api_url
    if not base:
        raise RuntimeError("API_URL not configured")
    url = f"{base.rstrip('/')}{path}"

    headers: dict[str, str] = {}
    if base_settings.internal_api_key:
        headers["Authorization"] = f"Bearer {base_settings.internal_api_key}"
    else:
        user_data = getattr(ctx, "user_data", None) if ctx is not None else None
        init_data = None
        if isinstance(user_data, dict):
            init_data = user_data.get("tg_init_data")
        if not isinstance(init_data, str):
            raise AuthRequiredError()
        headers["Authorization"] = f"tg {init_data}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return cast(dict[str, object], resp.json())
