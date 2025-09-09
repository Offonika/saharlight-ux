import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.diabetes.services import db
from services.api.app.telegram_auth import check_token


def test_patch_profile_returns_status_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.commit()

    async def run_db_wrapper(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    server.app.dependency_overrides[check_token] = lambda: {"id": 1}

    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={"timezone": "UTC", "timezoneAuto": False, "therapyType": "tablets"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "UTC"
        assert data["timezoneAuto"] is False
        assert data["sosAlertsEnabled"] is True
        assert data["sosContact"] is None
        assert data["therapyType"] == "tablets"

    server.app.dependency_overrides.clear()
