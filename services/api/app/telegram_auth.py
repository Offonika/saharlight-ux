import hashlib
import hmac
import json
import logging
import time
from typing import cast
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from . import config
from .schemas.user import UserContext


logger = logging.getLogger(__name__)

# Header carrying Telegram WebApp init data
TG_INIT_DATA_HEADER = "X-Telegram-Init-Data"

# Maximum allowed age of auth_date in seconds (24 hours)
AUTH_DATE_MAX_AGE = 24 * 60 * 60


_SETTINGS_CACHE: list[object] = []


def _remember_settings(candidate: object) -> None:
    for existing in _SETTINGS_CACHE:
        if existing is candidate:
            return
    _SETTINGS_CACHE.append(candidate)


_remember_settings(config.get_settings())


def _iter_settings_candidates() -> list[object]:
    """Return unique configuration objects to consult for the Telegram token."""

    current_candidates: list[object] = []
    for candidate in (
        config.get_settings(),
        getattr(config, "settings", None),
    ):
        if candidate is None:
            continue
        current_candidates.append(candidate)
        _remember_settings(candidate)

    candidates: list[object] = []
    seen_ids: set[int] = set()
    for candidate in current_candidates + _SETTINGS_CACHE:
        candidate_id = id(candidate)
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        candidates.append(candidate)
    return candidates


def parse_and_verify_init_data(init_data: str, token: str) -> dict[str, object]:
    """Parse and validate Telegram WebApp initialization data.

    Parameters
    ----------
    init_data:
        Raw query string received from Telegram WebApp.
    token:
        Bot token used to compute the validation hash.
    """
    now = time.time()
    if len(init_data) > 1024:
        raise HTTPException(status_code=413, detail="init data too long")
    try:
        pairs: list[tuple[str, str]] = parse_qsl(init_data, strict_parsing=True)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid init data") from exc
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=401, detail="duplicate parameter")
    params: dict[str, object] = dict(pairs)
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
    if auth_date > now + 60:
        raise HTTPException(status_code=401, detail="invalid auth date")
    if now - auth_date > AUTH_DATE_MAX_AGE:
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


def get_tg_user(init_data: str) -> UserContext:
    """Validate ``init_data`` and return Telegram ``user`` info."""
    token: str | None = None
    for candidate in _iter_settings_candidates():
        if candidate is None:
            continue
        value = getattr(candidate, "telegram_token", None)
        if not isinstance(value, str):
            continue
        if not value:
            continue
        token = value
        break
    if not token:
        logger.error("telegram token not configured")
        raise HTTPException(status_code=503, detail="telegram token not configured")
    data: dict[str, object] = parse_and_verify_init_data(init_data, token)
    user_raw = data.get("user")
    user = user_raw if isinstance(user_raw, dict) else None
    if user is None or not isinstance(user.get("id"), int):
        raise HTTPException(status_code=401, detail="invalid user")
    return cast(UserContext, user)


def require_tg_user(
    init_data: str | None = Header(None, alias=TG_INIT_DATA_HEADER),
    authorization: str | None = Header(None),
) -> UserContext:
    """Dependency ensuring request contains valid Telegram user info.

    Accepts Telegram init data from ``X-Telegram-Init-Data`` or
    ``Authorization: tg <init_data>`` header.
    """
    if (
        not init_data
        and isinstance(authorization, str)
        and authorization.startswith("tg ")
    ):
        init_data = authorization[3:]
    if not init_data:
        raise HTTPException(status_code=401, detail="missing init data")
    return get_tg_user(init_data)


def check_token(authorization: str | None = Header(None)) -> UserContext:
    """Validate Telegram init data passed via ``Authorization`` header."""
    if not authorization or not authorization.startswith("tg "):
        raise HTTPException(status_code=401, detail="missing init data")
    init_data = authorization[3:]
    return get_tg_user(init_data)
