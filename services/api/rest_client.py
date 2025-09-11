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


def _auth_headers(ctx: ContextTypes.DEFAULT_TYPE | None) -> dict[str, str]:
    """Build Authorization headers for API requests.

    Prefers the internal API key if present. Otherwise tries to extract
    ``tg_init_data`` from the provided ``ctx``.  The token may reside either in
    ``ctx.user_data`` or in the application's persistence storage.
    """

    settings = get_settings()
    if settings.internal_api_key:
        return {"Authorization": f"Bearer {settings.internal_api_key}"}

    init_data: str | None = None
    if ctx is not None:
        user_data = getattr(ctx, "user_data", None)
        if isinstance(user_data, dict):
            raw = user_data.get("tg_init_data")
            if isinstance(raw, str):
                init_data = raw

        if init_data is None:
            app = getattr(ctx, "application", None)
            user_id = getattr(ctx, "user_id", None)
            if user_id is None:
                user_id = getattr(ctx, "_user_id", None)
            if app is not None and user_id is not None:
                app_ud = getattr(app, "user_data", None)
                if isinstance(app_ud, dict):
                    stored = app_ud.get(user_id)
                    if isinstance(stored, dict):
                        raw = stored.get("tg_init_data")
                        if isinstance(raw, str):
                            init_data = raw
                if init_data is None:
                    persistence = getattr(app, "persistence", None)
                    if persistence is not None and hasattr(persistence, "get_user_data"):
                        stored = persistence.get_user_data(user_id)
                        if isinstance(stored, dict):
                            raw = stored.get("tg_init_data")
                            if isinstance(raw, str):
                                init_data = raw

    if init_data is not None:
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
    headers = _auth_headers(ctx)
    if not headers:
        raise AuthRequiredError()

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return cast(dict[str, object], resp.json())
