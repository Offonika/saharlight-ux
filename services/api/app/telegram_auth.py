import hashlib
import hmac
import json
import logging
import time
import weakref
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

_SETTINGS_CACHE: list[weakref.ReferenceType[object]] = []
_LAST_SEEN_SETTINGS_ID: int | None = None
_LAST_SEEN_SETTINGS_TYPE: type[object] | None = None


def _settings_type() -> type[object] | None:
    settings_cls = getattr(config, "Settings", None)
    return settings_cls if isinstance(settings_cls, type) else None


def _is_settings_instance(candidate: object) -> bool:
    settings_cls = _settings_type()
    return settings_cls is not None and isinstance(candidate, settings_cls)


def _remember_settings(candidate: object) -> None:
    if not _is_settings_instance(candidate):
        return

    for ref in list(_SETTINGS_CACHE):
        existing = ref()
        if existing is None:
            _SETTINGS_CACHE.remove(ref)
            continue
        if not _is_settings_instance(existing):
            _SETTINGS_CACHE.remove(ref)
            continue
        if existing is candidate:
            return

    try:
        _SETTINGS_CACHE.append(weakref.ref(candidate))
    except TypeError:
        # ``Settings`` should support weak references, but guard defensively.
        return


def _purge_obsolete_settings(current_settings: object | None) -> None:
    global _LAST_SEEN_SETTINGS_ID, _LAST_SEEN_SETTINGS_TYPE

    settings_cls = _settings_type()

    for ref in list(_SETTINGS_CACHE):
        target = ref()
        if target is None:
            _SETTINGS_CACHE.remove(ref)
            continue
        if settings_cls is not None and not isinstance(target, settings_cls):
            _SETTINGS_CACHE.remove(ref)

    module_settings_id = id(current_settings) if current_settings is not None else None

    type_changed = (
        _LAST_SEEN_SETTINGS_TYPE is not None
        and settings_cls is not None
        and settings_cls is not _LAST_SEEN_SETTINGS_TYPE
    )
    instance_changed = (
        _LAST_SEEN_SETTINGS_ID is not None
        and module_settings_id is not None
        and module_settings_id != _LAST_SEEN_SETTINGS_ID
    )

    if type_changed or instance_changed:
        _SETTINGS_CACHE.clear()

    _LAST_SEEN_SETTINGS_TYPE = settings_cls
    _LAST_SEEN_SETTINGS_ID = module_settings_id


_remember_settings(config.get_settings())


def _iter_settings_candidates() -> list[tuple[object, bool]]:
    """Return configuration objects to consult for the Telegram token.

    The returned list preserves the order in which candidates should be
    consulted. Each tuple contains the candidate object and a flag signalling
    whether it represents the *current* settings instance (``True``) or a
    cached historical one (``False``).
    """

    module_settings = getattr(config, "settings", None)
    _purge_obsolete_settings(module_settings)

    candidates: list[tuple[object, bool]] = []
    seen_ids: set[int] = set()
    settings_cls = _settings_type()
    active_settings = config.get_settings()

    def consider(candidate: object | None, is_current_hint: bool) -> None:
        if candidate is None:
            return
        candidate_id = id(candidate)
        if candidate_id in seen_ids:
            return

        if candidate is module_settings:
            is_current = True
        elif settings_cls is not None and isinstance(candidate, settings_cls):
            is_current = is_current_hint
        elif candidate is active_settings:
            is_current = is_current_hint
        elif hasattr(candidate, "telegram_token"):
            is_current = False
        else:
            return

        seen_ids.add(candidate_id)
        candidates.append((candidate, is_current))
        _remember_settings(candidate)

    consider(module_settings, True)
    consider(active_settings, True)

    for ref in list(_SETTINGS_CACHE):
        cached = ref()
        if cached is None:
            _SETTINGS_CACHE.remove(ref)
            continue
        consider(cached, False)

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

    primary_tokens: list[str] = []
    cached_tokens: list[str] = []
    for candidate, is_current in _iter_settings_candidates():
        value = getattr(candidate, "telegram_token", None)
        if not isinstance(value, str) or not value:
            continue
        if is_current:
            primary_tokens.append(value)
        else:
            cached_tokens.append(value)

    tokens: list[str] = [*primary_tokens, *cached_tokens]
    if not tokens:
        logger.error("telegram token not configured")
        raise HTTPException(status_code=503, detail="telegram token not configured")

    last_invalid_hash_error: HTTPException | None = None
    data: dict[str, object] | None = None
    for token in tokens:
        try:
            data = parse_and_verify_init_data(init_data, token)
        except HTTPException as exc:
            if exc.status_code == 401 and exc.detail == "invalid hash":
                last_invalid_hash_error = exc
                continue
            raise
        else:
            break

    if data is None:
        if last_invalid_hash_error is not None:
            raise last_invalid_hash_error
        raise HTTPException(status_code=401, detail="invalid init data")

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
