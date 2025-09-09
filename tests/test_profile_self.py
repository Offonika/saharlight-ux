import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.config import settings
from services.api.app.main import app

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def test_profile_self_valid_header(monkeypatch: pytest.MonkeyPatch, in_memory_db: sessionmaker[Session]) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    from services.api.app import main as main_module
    from services.api.app.routers import profile as profile_router

    from types import SimpleNamespace

    async def _fake_get_learning_profile(user_id: int) -> Any:
        return SimpleNamespace(
            id=user_id,
            age_group=None,
            learning_level=None,
            diabetes_type=None,
        )

    monkeypatch.setattr(profile_router, "get_learning_profile", _fake_get_learning_profile)

    monkeypatch.setattr(main_module, "init_db", lambda: None)
    async def _fake_run_db(*args: Any, **kwargs: Any) -> int:
        return 0
    monkeypatch.setattr(main_module, "run_db", _fake_run_db)

    init_data = build_init_data(42)
    with TestClient(app) as client:
        resp = client.get("/api/profile/self", headers={"Authorization": f"tg {init_data}"})

    assert resp.status_code == 200
    assert resp.json()["id"] == 42


def test_profile_self_missing_header() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/profile/self")
    assert resp.status_code == 401


def test_profile_self_invalid_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    with TestClient(app) as client:
        resp = client.get("/api/profile/self", headers={"Authorization": "tg bad"})

    assert resp.status_code == 401
