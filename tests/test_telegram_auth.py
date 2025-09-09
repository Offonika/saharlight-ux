import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any

import pytest
from fastapi import HTTPException

from services.api.app.config import settings
from services.api.app.schemas.user import UserContext
from services.api.app.telegram_auth import (
    AUTH_DATE_MAX_AGE,
    parse_and_verify_init_data,
    require_tg_user,
)

TOKEN = "test-token"


def build_init_data(
    token: str = TOKEN, user_id: int | str = 1, auth_date: int | None = None
) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    if auth_date is None:
        auth_date = int(time.time())
    params = {
        "auth_date": str(auth_date),
        "query_id": "abc",
        "user": user,
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def test_parse_and_verify_init_data_valid() -> None:
    init_data: str = build_init_data()
    data: dict[str, Any] = parse_and_verify_init_data(init_data, TOKEN)
    assert data["user"]["id"] == 1
    assert isinstance(data["user"]["id"], int)


def test_parse_and_verify_init_data_invalid_hash() -> None:
    init_data: str = build_init_data()
    parts: dict[str, str] = dict(urllib.parse.parse_qsl(init_data))
    parts["hash"] = "0" * 64
    tampered: str = urllib.parse.urlencode(parts)
    with pytest.raises(HTTPException):
        parse_and_verify_init_data(tampered, TOKEN)


def test_parse_and_verify_init_data_invalid_user_json() -> None:
    params = {
        "auth_date": str(int(time.time())),
        "query_id": "abc",
        "user": "{bad",
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    init_data = urllib.parse.urlencode(params)
    with pytest.raises(HTTPException) as exc:
        parse_and_verify_init_data(init_data, TOKEN)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid user data"


def test_parse_and_verify_init_data_too_long() -> None:
    init_data = "a" * 1025
    with pytest.raises(HTTPException) as exc:
        parse_and_verify_init_data(init_data, TOKEN)
    assert exc.value.status_code == 413
    assert exc.value.detail == "init data too long"


def test_require_tg_user_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data: str = build_init_data()
    user: UserContext = require_tg_user(init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)


def test_require_tg_user_invalid_id_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data: str = build_init_data(user_id="bad")
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid user"


def test_require_tg_user_missing() -> None:
    with pytest.raises(HTTPException):
        require_tg_user(None)


def test_require_tg_user_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    with pytest.raises(HTTPException):
        require_tg_user("bad")


def test_require_tg_user_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Requests fail with a clear error if the bot token is not configured."""
    monkeypatch.setattr(settings, "telegram_token", "")
    with pytest.raises(HTTPException) as exc:
        require_tg_user("whatever")
    assert exc.value.status_code == 503


def test_parse_and_verify_init_data_expired() -> None:
    past = int(time.time()) - (AUTH_DATE_MAX_AGE + 1)
    init_data = build_init_data(auth_date=past)
    with pytest.raises(HTTPException) as exc:
        parse_and_verify_init_data(init_data, TOKEN)
    assert exc.value.status_code == 401
    assert exc.value.detail == "expired auth data"


def test_parse_and_verify_init_data_future() -> None:
    future = int(time.time()) + 61
    init_data = build_init_data(auth_date=future)
    with pytest.raises(HTTPException) as exc:
        parse_and_verify_init_data(init_data, TOKEN)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid auth date"


def test_require_tg_user_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    past = int(time.time()) - (AUTH_DATE_MAX_AGE + 1)
    init_data = build_init_data(auth_date=past)
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 401
    assert exc.value.detail == "expired auth data"


def test_require_tg_user_future(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    future = int(time.time()) + 61
    init_data = build_init_data(auth_date=future)
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid auth date"
