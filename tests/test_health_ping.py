from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.routers import health


def _make_session_factory() -> sessionmaker[Session]:
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return sessionmaker(bind=engine, class_=Session)


def test_ping_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "SessionLocal", _make_session_factory(), raising=False)
    with TestClient(server.app) as client:
        resp = client.get("/api/health/ping")
    assert resp.status_code == 200
    assert resp.json() == {"status": "up"}


def test_ping_down(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_run_db(
        *args: object, **kwargs: object
    ) -> None:  # pragma: no cover - used in test
        raise RuntimeError("fail")

    monkeypatch.setattr(health, "run_db", fail_run_db, raising=False)
    with TestClient(server.app) as client:
        resp = client.get("/api/health/ping")
    assert resp.status_code == 503
    assert resp.json() == {"status": "down"}
