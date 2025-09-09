"""Authorization tests for billing endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from services.api.app.config import settings
from services.api.app.main import app
from services.api.app.routers import billing
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER
from services.api.app.billing.config import BillingSettings


TOKEN = "test-token"


def build_init_data(token: str = TOKEN, user_id: int = 1) -> str:
    """Create signed init data for Telegram WebApp."""

    user = json.dumps({"id": user_id}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Test client with billing enabled."""

    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    with TestClient(app) as test_client:
        test_client.app.dependency_overrides.clear()
        test_client.app.dependency_overrides[billing._require_billing_enabled] = (
            lambda: BillingSettings(
                billing_enabled=True,
                billing_test_mode=True,
                billing_provider="dummy",
                paywall_mode="soft",
            )
        )
        try:
            yield test_client
        finally:
            test_client.app.dependency_overrides.clear()


def test_pay_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/billing/pay", params={"user_id": 1})
    assert resp.status_code == 401


def test_pay_id_mismatch(client: TestClient) -> None:
    init_data = build_init_data()
    resp = client.post(
        "/api/billing/pay",
        params={"user_id": 2},
        headers={TG_INIT_DATA_HEADER: init_data},
    )
    assert resp.status_code == 403


def test_trial_id_mismatch(client: TestClient) -> None:
    init_data = build_init_data()
    resp = client.post(
        "/api/billing/trial",
        params={"user_id": 2},
        headers={TG_INIT_DATA_HEADER: init_data},
    )
    assert resp.status_code == 403


def test_trial_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/billing/trial", params={"user_id": 1})
    assert resp.status_code == 401


def test_subscribe_id_mismatch(client: TestClient) -> None:
    init_data = build_init_data()
    resp = client.post(
        "/api/billing/subscribe",
        params={"user_id": 2, "plan": "pro"},
        headers={TG_INIT_DATA_HEADER: init_data},
    )
    assert resp.status_code == 403


def test_subscribe_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    assert resp.status_code == 401
