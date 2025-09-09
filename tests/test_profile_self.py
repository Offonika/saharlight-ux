import hashlib
import hmac
import json
import time
import urllib.parse

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from services.api.app.config import settings
from services.api.app.routers.profile import router as profile_router

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


@pytest.mark.skip("db not initialized in test environment")
def test_profile_self_valid_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    from services.api.app.assistant.repositories import learning_profile as lp
    monkeypatch.setattr(lp, "get_learning_profile", lambda _uid: None)
    app = FastAPI()
    app.include_router(profile_router)

    init_data = build_init_data(42)
    with TestClient(app) as client:
        resp = client.get("/profile/self", headers={"Authorization": f"tg {init_data}"})

    assert resp.status_code == 200
    assert resp.json()["id"] == 42


def test_profile_self_missing_header() -> None:
    app = FastAPI()
    app.include_router(profile_router)
    with TestClient(app) as client:
        resp = client.get("/profile/self")
    assert resp.status_code == 401


def test_profile_self_invalid_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    app = FastAPI()
    app.include_router(profile_router)
    with TestClient(app) as client:
        resp = client.get("/profile/self", headers={"Authorization": "tg bad"})

    assert resp.status_code == 401
