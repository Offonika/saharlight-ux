import hashlib
import hmac
import json
import urllib.parse

import pytest
from fastapi import HTTPException

from services.api.app.config import settings
from services.api.app.telegram_auth import parse_and_verify_init_data, require_tg_user

TOKEN = "test-token"


def build_init_data(token: str = TOKEN, user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {
        "auth_date": "123",
        "query_id": "abc",
        "user": user,
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def test_parse_and_verify_init_data_valid() -> None:
    init_data = build_init_data()
    data = parse_and_verify_init_data(init_data, TOKEN)
    assert data["user"]["id"] == 1


def test_parse_and_verify_init_data_invalid_hash() -> None:
    init_data = build_init_data()
    parts = dict(urllib.parse.parse_qsl(init_data))
    parts["hash"] = "0" * 64
    tampered = urllib.parse.urlencode(parts)
    with pytest.raises(HTTPException):
        parse_and_verify_init_data(tampered, TOKEN)


def test_require_tg_user_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data()
    user = require_tg_user(init_data)
    assert user["id"] == 1


def test_require_tg_user_missing() -> None:
    with pytest.raises(HTTPException):
        require_tg_user(None)


def test_require_tg_user_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    with pytest.raises(HTTPException):
        require_tg_user("bad")
