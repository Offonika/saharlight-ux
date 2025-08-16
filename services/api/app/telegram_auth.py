import hashlib
import hmac
import json
import logging
from typing import Any
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from .config import settings


logger = logging.getLogger(__name__)


def parse_and_verify_init_data(init_data: str, token: str) -> dict[str, Any]:
    """Parse and validate Telegram WebApp initialization data.

    Parameters
    ----------
    init_data:
        Raw query string received from Telegram WebApp.
    token:
        Bot token used to compute the validation hash.
    """
    try:
        params: dict[str, Any] = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid init data") from exc
    auth_hash = params.pop("hash", None)
    if not auth_hash:
        raise HTTPException(status_code=401, detail="missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(check, auth_hash):
        raise HTTPException(status_code=401, detail="invalid hash")

    if "user" in params:
        params["user"] = json.loads(params["user"])
    return params


def require_tg_user(
    init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
) -> dict[str, Any]:
    """Dependency ensuring request contains valid Telegram user info."""
    if not init_data:
        raise HTTPException(status_code=401, detail="missing init data")

    token: str | None = settings.telegram_token
    if not token:
        logger.error("telegram token not configured")
        raise HTTPException(status_code=500, detail="server misconfigured")

    data: dict[str, Any] = parse_and_verify_init_data(init_data, token)
    user: dict[str, Any] | None = data.get("user")
    if not isinstance(user, dict) or "id" not in user:
        raise HTTPException(status_code=401, detail="invalid user")
    return user
