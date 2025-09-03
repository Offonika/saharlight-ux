from __future__ import annotations

from fastapi.testclient import TestClient

from services.api.app.billing import reload_billing_settings
from services.api.app.main import app


def test_billing_disabled(monkeypatch) -> None:
    monkeypatch.setenv("BILLING_ENABLED", "false")
    reload_billing_settings()
    with TestClient(app) as client:
        response = client.post("/api/billing/pay")
    assert response.status_code == 503


def test_dummy_provider(monkeypatch) -> None:
    monkeypatch.setenv("BILLING_ENABLED", "true")
    monkeypatch.setenv("BILLING_PROVIDER", "dummy")
    monkeypatch.setenv("BILLING_TEST_MODE", "true")
    reload_billing_settings()
    with TestClient(app) as client:
        response = client.post("/api/billing/pay")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "test_mode": True}

