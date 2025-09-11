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


async def _auth_headers(ctx: ContextTypes.DEFAULT_TYPE | None) -> dict[str, str]:
    """Return authorization headers based on context or persistence."""

    settings = get_settings()
    if settings.internal_api_key:
        return {"Authorization": f"Bearer {settings.internal_api_key}"}

    init_data: str | None = None
    user_data = getattr(ctx, "user_data", None) if ctx is not None else None
    if isinstance(user_data, dict):
        init_data = cast(str | None, user_data.get("tg_init_data"))
    if not isinstance(init_data, str) and ctx is not None:
        application = getattr(ctx, "application", None)
        persistence = getattr(application, "persistence", None) if application else None
        user_id = getattr(ctx, "user_id", None) or getattr(ctx, "_user_id", None)
        if user_id is None:
            pair = getattr(ctx, "_user_id_and_chat_id", None)
            if pair is not None:
                user_id = pair[0]
        if persistence is not None and user_id is not None:
            try:
                persisted_all = await persistence.get_user_data()
            except TypeError:  # pragma: no cover - sync persistence
                persisted_all = persistence.get_user_data()
            if isinstance(persisted_all, dict):
                user_dict = persisted_all.get(user_id)
                if isinstance(user_dict, dict):
                    init_data = cast(str | None, user_dict.get("tg_init_data"))
                    if isinstance(init_data, str) and isinstance(user_data, dict):
                        user_data["tg_init_data"] = init_data

    if isinstance(init_data, str):
        return {"Authorization": f"tg {init_data}"}
    return {}


async def get_json(
    path: str, ctx: ContextTypes.DEFAULT_TYPE | None = None
) -> dict[str, object]:
    base_settings = get_settings()
    base = base_settings.api_url
    if not base:
        raise RuntimeError("API_URL not configured")
    url = f"{base.rstrip('/')}{path}"

    headers = await _auth_headers(ctx)
    if not headers:
        raise AuthRequiredError()

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return cast(dict[str, object], resp.json())
