import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import Base
from services.api.app.services import profile as profile_service
from services.api.app.legacy import router


def test_profiles_get_requires_telegram_id() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        resp = client.get("/api/profiles")
    assert resp.status_code == 422


def test_profiles_post_creates_user_for_missing_telegram_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(profile_service, "SessionLocal", TestSession)
    payload = {
        "telegramId": 777,
        "icr": 1.0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "orgId": 1,
    }
    with TestClient(app) as client:
        resp = client.post("/api/profiles", json=payload)
    assert resp.status_code == 200
    engine.dispose()
