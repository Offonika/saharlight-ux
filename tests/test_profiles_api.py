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
        "cf": 2.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "orgId": 1,
    }
    with TestClient(app) as client:
        resp = client.post("/api/profiles", json=payload)
    assert resp.status_code == 200
    engine.dispose()


def test_profiles_post_invalid_values_returns_422(
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
        "low": 6.0,
        "high": 5.0,
    }
    with TestClient(app) as client:
        resp = client.post("/api/profiles", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"].endswith("low must be less than high")
    engine.dispose()


def test_profiles_post_invalid_icr_returns_422(
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
        "icr": 0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
    }
    with TestClient(app) as client:
        resp = client.post("/api/profiles", json=payload)
    assert resp.status_code == 422
    assert resp.json() == {"detail": "icr must be greater than 0"}
    engine.dispose()


def test_profiles_post_invalid_cf_returns_422(
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
        "cf": -1,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
    }
    with TestClient(app) as client:
        resp = client.post("/api/profiles", json=payload)
    assert resp.status_code == 422
    assert resp.json() == {"detail": "cf must be greater than 0"}
    engine.dispose()


def test_profiles_post_updates_existing_profile(
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
    with TestClient(app) as client:
        payload = {
            "telegramId": 777,
            "icr": 1.0,
            "cf": 2.0,
            "target": 5.0,
            "low": 4.0,
            "high": 6.0,
            "quietStart": "23:00:00",
            "quietEnd": "07:00:00",
        }
        assert client.post("/api/profiles", json=payload).status_code == 200

        update = {
            "telegramId": 777,
            "icr": 1.5,
            "cf": 2.5,
            "target": 6.0,
            "low": 5.0,
            "high": 7.0,
            "quietStart": "22:00:00",
            "quietEnd": "06:00:00",
        }
        assert client.post("/api/profiles", json=update).status_code == 200

        resp = client.get("/api/profiles", params={"telegramId": 777})
        assert resp.status_code == 200
        data = resp.json()
        assert data["icr"] == 1.5
        assert data["cf"] == 2.5
        assert data["quietStart"] == "22:00:00"
        assert data["quietEnd"] == "06:00:00"
    engine.dispose()
