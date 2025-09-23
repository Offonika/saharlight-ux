import hashlib
import hmac
import json
import time
import urllib.parse

import pytest
from fastapi.testclient import TestClient

from services.api.app import config
from services.api.app.main import app
from services.api.app.schemas.stats import DayStats
from services.api.app.routers import stats as stats_router

TOKEN = "test-token"


def build_init_data(user_id: int = 1, token: str = TOKEN) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def test_stats_valid_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data = build_init_data(42)
    with TestClient(app) as client:
        async def fake_get_day_stats(_: int) -> DayStats:
            return DayStats(sugar=5.7, breadUnits=3, insulin=10)

        monkeypatch.setattr(stats_router, "get_day_stats", fake_get_day_stats)

        resp = client.get(
            "/api/stats",
            params={"telegramId": 42},
            headers={"Authorization": f"tg {init_data}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"sugar", "breadUnits", "insulin"}


def test_stats_missing_header() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/stats", params={"telegramId": 1})
    assert resp.status_code == 401


def test_stats_mismatched_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data = build_init_data(1)
    with TestClient(app) as client:
        resp = client.get(
            "/api/stats",
            params={"telegramId": 2},
            headers={"Authorization": f"tg {init_data}"},
        )
    assert resp.status_code == 403


def test_empty_stats_returns_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data = build_init_data(11)
    with TestClient(app) as client:
        async def fake_get_day_stats(_: int) -> DayStats:
            return DayStats(sugar=5.7, breadUnits=3, insulin=10)

        monkeypatch.setattr(stats_router, "get_day_stats", fake_get_day_stats)

        resp = client.get(
            "/api/stats",
            params={"telegramId": 11},
            headers={"Authorization": f"tg {init_data}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"sugar": 5.7, "breadUnits": 3, "insulin": 10}


def test_analytics_valid_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data = build_init_data(7)
    with TestClient(app) as client:
        resp = client.get(
            "/api/analytics",
            params={"telegramId": 7},
            headers={"Authorization": f"tg {init_data}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body and body[0].get("date")


def test_analytics_mismatched_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data = build_init_data(1)
    with TestClient(app) as client:
        resp = client.get(
            "/api/analytics",
            params={"telegramId": 2},
            headers={"Authorization": f"tg {init_data}"},
        )
    assert resp.status_code == 403


def test_stats_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    init_data = build_init_data(5)

    async def fake_get_day_stats(_: int) -> DayStats | None:
        return None

    monkeypatch.setattr(stats_router, "get_day_stats", fake_get_day_stats)

    with TestClient(app) as client:
        resp = client.get(
            "/api/stats",
            params={"telegramId": 5},
            headers={"Authorization": f"tg {init_data}"},
        )
    assert resp.status_code == 204
    assert resp.content == b""


def test_stats_authorizes_after_token_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "telegram_token", TOKEN)
    user_id = 21

    async def fake_get_day_stats(_: int) -> DayStats:
        return DayStats(sugar=5.7, breadUnits=3, insulin=10)

    monkeypatch.setattr(stats_router, "get_day_stats", fake_get_day_stats)

    with TestClient(app) as client:
        initial_init_data = build_init_data(user_id=user_id, token=TOKEN)
        resp = client.get(
            "/api/stats",
            params={"telegramId": user_id},
            headers={"Authorization": f"tg {initial_init_data}"},
        )
        assert resp.status_code == 200

        monkeypatch.setattr(config.settings, "telegram_token", "")
        resp_missing = client.get(
            "/api/stats",
            params={"telegramId": user_id},
            headers={"Authorization": f"tg {initial_init_data}"},
        )
        assert resp_missing.status_code == 503

        patched_token = "patched-token"
        monkeypatch.setattr(config.settings, "telegram_token", patched_token)
        patched_init_data = build_init_data(user_id=user_id, token=patched_token)
        resp_patched = client.get(
            "/api/stats",
            params={"telegramId": user_id},
            headers={"Authorization": f"tg {patched_init_data}"},
        )
        assert resp_patched.status_code == 200
