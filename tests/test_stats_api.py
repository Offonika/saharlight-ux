import hashlib
import hmac
import json
import time
import urllib.parse

import pytest
from fastapi.testclient import TestClient

from services.api.app.config import settings
from services.api.app.main import app
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def test_stats_valid_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data(42)
    with TestClient(app) as client:
        resp = client.get(
            "/stats",
            params={"telegramId": 42},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"sugar", "breadUnits", "insulin"}


def test_stats_missing_header() -> None:
    with TestClient(app) as client:
        resp = client.get("/stats", params={"telegramId": 1})
    assert resp.status_code == 401


def test_stats_mismatched_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data(1)
    with TestClient(app) as client:
        resp = client.get(
            "/stats",
            params={"telegramId": 2},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 403


def test_empty_stats_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data(11)
    with TestClient(app) as client:
        resp = client.get(
            "/stats",
            params={"telegramId": 11},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code in (200, 204)
    if resp.status_code == 200:
        assert resp.json() == {"sugar": 5.7, "breadUnits": 3, "insulin": 10}
    else:
        assert resp.content == b""


def test_analytics_valid_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data(7)
    with TestClient(app) as client:
        resp = client.get(
            "/analytics",
            params={"telegramId": 7},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body and body[0].get("date")
