from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.main import app
from services.api.app.routers import health


def test_ping_returns_503_when_db_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_run_db(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(health, "run_db", fail_run_db)
    from services.api.app import main
    monkeypatch.setattr(main, "init_db", lambda: None)

    with TestClient(app) as client:
        resp = client.get("/api/health/ping")

    assert resp.status_code == 503
    assert resp.json() == {"status": "down"}
