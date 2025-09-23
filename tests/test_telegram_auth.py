import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any

import pytest
from fastapi import HTTPException

from services.api.app import config
from services.api.app.schemas.user import UserContext
from services.api.app.telegram_auth import (
    AUTH_DATE_MAX_AGE,
    check_token,
    get_tg_user,
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


def test_parse_and_verify_init_data_duplicate_param() -> None:
    init_data = build_init_data()
    tampered = f"{init_data}&auth_date=1"
    with pytest.raises(HTTPException) as exc:
        parse_and_verify_init_data(tampered, TOKEN)
    assert exc.value.status_code == 401
    assert exc.value.detail == "duplicate parameter"


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
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data: str = build_init_data()
    user: UserContext = require_tg_user(init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)


def test_require_tg_user_prefers_runtime_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub = object()
    monkeypatch.setattr(config, "get_settings", lambda: stub)
    patched_token = "patched-token"
    monkeypatch.setattr(config.settings, "telegram_token", patched_token)
    init_data = build_init_data(token=patched_token)
    user = require_tg_user(init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)

    monkeypatch.setattr(config.settings, "telegram_token", "")
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 503

    patched_token = "patched-token-2"
    monkeypatch.setattr(config.settings, "telegram_token", patched_token)
    init_data = build_init_data(token=patched_token)
    user = require_tg_user(init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)


def test_require_tg_user_token_cleared_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    patched_token = "cached-token"
    monkeypatch.setattr(config.settings, "telegram_token", patched_token)

    init_data = build_init_data(token=patched_token)
    user = require_tg_user(init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)

    config.settings.telegram_token = ""
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 503
    assert exc.value.detail == "telegram token not configured"


def test_require_and_check_use_updated_token(monkeypatch: pytest.MonkeyPatch) -> None:
    initial_token = "initial-token"
    monkeypatch.setattr(config.settings, "telegram_token", initial_token)

    init_data_old = build_init_data(token=initial_token)
    user_old = require_tg_user(init_data_old)
    assert user_old["id"] == 1
    header_old = f"tg {init_data_old}"
    user_old_header = check_token(header_old)
    assert user_old_header["id"] == 1

    updated_token = "updated-token"
    config.settings.telegram_token = updated_token

    init_data_new = build_init_data(token=updated_token)
    user_new = require_tg_user(init_data_new)
    assert user_new["id"] == 1
    header_new = f"tg {init_data_new}"
    user_new_header = check_token(header_new)
    assert user_new_header["id"] == 1

    with pytest.raises(HTTPException) as exc_require:
        require_tg_user(init_data_old)
    assert exc_require.value.status_code == 401
    assert exc_require.value.detail == "invalid hash"

    with pytest.raises(HTTPException) as exc_check:
        check_token(header_old)
    assert exc_check.value.status_code == 401
    assert exc_check.value.detail == "invalid hash"


def test_require_tg_user_after_config_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    initial_init_data = build_init_data()
    user = require_tg_user(initial_init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)

    proxy_before = config.settings
    reloaded_settings = config.reload_settings()
    assert config.get_settings() is reloaded_settings
    assert config.settings is proxy_before

    with pytest.raises(HTTPException) as exc:
        require_tg_user(initial_init_data)
    assert exc.value.status_code == 503
    assert exc.value.detail == "telegram token not configured"

    patched_token = "reloaded-token"
    monkeypatch.setattr(config.settings, "telegram_token", patched_token)
    assert reloaded_settings.telegram_token == patched_token
    patched_init_data = build_init_data(token=patched_token)
    user = require_tg_user(patched_init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)

    with pytest.raises(HTTPException) as exc_old:
        require_tg_user(initial_init_data)
    assert exc_old.value.status_code == 401
    assert exc_old.value.detail == "invalid hash"


def test_require_tg_user_config_reload_requires_new_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    patched_token = "reload-token"
    monkeypatch.setattr(config.settings, "telegram_token", patched_token)
    initial_init_data = build_init_data(token=patched_token)
    user = require_tg_user(initial_init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)

    reloaded_settings = config.reload_settings()
    assert config.get_settings() is reloaded_settings

    with pytest.raises(HTTPException) as exc:
        require_tg_user(initial_init_data)
    assert exc.value.status_code == 503
    assert exc.value.detail == "telegram token not configured"

    replacement_token = "replacement-token"
    monkeypatch.setattr(config.settings, "telegram_token", replacement_token)
    assert reloaded_settings.telegram_token == replacement_token
    patched_init_data = build_init_data(token=replacement_token)
    user = require_tg_user(patched_init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)

    with pytest.raises(HTTPException) as exc_old:
        require_tg_user(initial_init_data)
    assert exc_old.value.status_code == 401
    assert exc_old.value.detail == "invalid hash"


def test_require_and_check_use_reloaded_settings_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    initial_token = "initial-reload-token"
    monkeypatch.setattr(config.settings, "telegram_token", initial_token)

    init_data_old = build_init_data(token=initial_token)
    require_tg_user(init_data_old)
    header_old = f"tg {init_data_old}"
    check_token(header_old)

    reloaded_settings = config.reload_settings()
    assert config.get_settings() is reloaded_settings

    with pytest.raises(HTTPException) as exc_require_missing:
        require_tg_user(init_data_old)
    assert exc_require_missing.value.status_code == 503
    assert exc_require_missing.value.detail == "telegram token not configured"

    with pytest.raises(HTTPException) as exc_check_missing:
        check_token(header_old)
    assert exc_check_missing.value.status_code == 503
    assert exc_check_missing.value.detail == "telegram token not configured"

    updated_token = "reloaded-token"
    monkeypatch.setattr(config.settings, "telegram_token", updated_token)
    assert reloaded_settings.telegram_token == updated_token

    init_data_new = build_init_data(token=updated_token)
    user_new = require_tg_user(init_data_new)
    assert user_new["id"] == 1
    header_new = f"tg {init_data_new}"
    user_new_header = check_token(header_new)
    assert user_new_header["id"] == 1

    with pytest.raises(HTTPException) as exc_require_old:
        require_tg_user(init_data_old)
    assert exc_require_old.value.status_code == 401
    assert exc_require_old.value.detail == "invalid hash"

    with pytest.raises(HTTPException) as exc_check_old:
        check_token(header_old)
    assert exc_check_old.value.status_code == 401
    assert exc_check_old.value.detail == "invalid hash"


def test_require_tg_user_invalid_id_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data: str = build_init_data(user_id="bad")
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid user"


def test_require_tg_user_missing() -> None:
    with pytest.raises(HTTPException) as exc:
        require_tg_user(None)
    assert exc.value.status_code == 401
    assert exc.value.detail == "missing init data"


def test_require_tg_user_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    with pytest.raises(HTTPException):
        require_tg_user("bad")


def test_require_tg_user_authorization_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data: str = build_init_data()
    header = f"tg {init_data}"
    user: UserContext = require_tg_user(None, header)
    assert user["id"] == 1


def test_require_tg_user_empty_authorization() -> None:
    header = "tg "
    with pytest.raises(HTTPException) as exc:
        require_tg_user(None, header)
    assert exc.value.status_code == 401
    assert exc.value.detail == "missing init data"


def test_require_tg_user_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Requests fail with a clear error if the bot token is not configured."""
    monkeypatch.setattr(config.settings, "telegram_token", "")
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
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    past = int(time.time()) - (AUTH_DATE_MAX_AGE + 1)
    init_data = build_init_data(auth_date=past)
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 401
    assert exc.value.detail == "expired auth data"


def test_require_tg_user_future(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    future = int(time.time()) + 61
    init_data = build_init_data(auth_date=future)
    with pytest.raises(HTTPException) as exc:
        require_tg_user(init_data)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid auth date"


def test_get_tg_user_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data: str = build_init_data()
    user: UserContext = get_tg_user(init_data)
    assert user["id"] == 1
    assert isinstance(user["id"], int)


def test_check_token_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data: str = build_init_data()
    header = f"tg {init_data}"
    user: UserContext = check_token(header)
    assert user["id"] == 1
    assert isinstance(user["id"], int)


def test_check_token_invalid_prefix() -> None:
    with pytest.raises(HTTPException) as exc:
        check_token("bearer bad")
    assert exc.value.status_code == 401
    assert exc.value.detail == "missing init data"


def test_check_token_invalid_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data: str = build_init_data(user_id="bad")
    header = f"tg {init_data}"
    with pytest.raises(HTTPException) as exc:
        check_token(header)
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid user"


def test_check_token_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", "")
    with pytest.raises(HTTPException) as exc:
        check_token("tg whatever")
    assert exc.value.status_code == 503
