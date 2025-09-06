import hashlib
import hmac
import json
import logging
import time
from typing import cast
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from .config import settings
from .schemas.user import UserContext


logger = logging.getLogger(__name__)

# Header carrying Telegram WebApp init data
TG_INIT_DATA_HEADER = "X-Telegram-Init-Data"

# Maximum allowed age of auth_date in seconds (24 hours)
AUTH_DATE_MAX_AGE = 24 * 60 * 60


def parse_and_verify_init_data(init_data: str, token: str) -> dict[str, object]:
    """Parse and validate Telegram WebApp initialization data.

    Parameters
    ----------
    init_data:
        Raw query string received from Telegram WebApp.
    token:
        Bot token used to compute the validation hash.
    """
    if len(init_data) > 1024:
        raise HTTPException(status_code=413, detail="init data too long")
    try:
        params: dict[str, object] = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid init data") from exc
    auth_hash_obj = params.pop("hash", None)
    if not isinstance(auth_hash_obj, str):
        raise HTTPException(status_code=401, detail="missing hash")
    auth_hash = auth_hash_obj

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(check, auth_hash):
        raise HTTPException(status_code=401, detail="invalid hash")

    auth_date_raw = params.get("auth_date")
    if not isinstance(auth_date_raw, (str, int)):
        raise HTTPException(status_code=401, detail="invalid auth date")
    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid auth date") from exc
    if time.time() - auth_date > AUTH_DATE_MAX_AGE:
        raise HTTPException(status_code=401, detail="expired auth data")
    params["auth_date"] = auth_date

    user_raw = params.get("user")
    if user_raw is not None:
        if not isinstance(user_raw, str):
            raise HTTPException(status_code=401, detail="invalid user data")
        try:
            params["user"] = json.loads(user_raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=401, detail="invalid user data") from exc
    return params


def require_tg_user(
    init_data: str | None = Header(None, alias=TG_INIT_DATA_HEADER),
) -> UserContext:
    """Dependency ensuring request contains valid Telegram user info."""
    if not init_data:
        raise HTTPException(status_code=401, detail="missing init data")

    token: str | None = settings.telegram_token
    if not token:
        logger.error("telegram token not configured")
        raise HTTPException(status_code=500, detail="server misconfigured")

    data: dict[str, object] = parse_and_verify_init_data(init_data, token)
    user_raw = data.get("user")
    user = user_raw if isinstance(user_raw, dict) else None
    if user is None or not isinstance(user.get("id"), int):
        raise HTTPException(status_code=401, detail="invalid user")
    return cast(UserContext, user)


def check_token(authorization: str | None = Header(None)) -> UserContext:
    """Validate Telegram init data passed via ``Authorization`` header."""
    if not authorization or not authorization.startswith("tg "):
        raise HTTPException(status_code=401, detail="missing init data")
    init_data = authorization[3:]
    token: str | None = settings.telegram_token
    if not token:
        logger.error("telegram token not configured")
        raise HTTPException(status_code=500, detail="server misconfigured")
    data: dict[str, object] = parse_and_verify_init_data(init_data, token)
    user_raw = data.get("user")
    user = user_raw if isinstance(user_raw, dict) else None
    if user is None or not isinstance(user.get("id"), int):
        raise HTTPException(status_code=401, detail="invalid user")
    return cast(UserContext, user)
