import logging
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import Base
import services.api.app.diabetes.services.db as db
from services.api.app.legacy import router


def test_profiles_get_requires_telegram_id() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        resp = client.get("/api/profiles")
    assert resp.status_code == 422


def test_profiles_get_invalid_telegram_id_returns_422() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        resp = client.get("/api/profiles", params={"telegramId": -1})
    assert resp.status_code == 422


def test_profiles_get_missing_profile_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
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
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=TestSession, **kwargs)

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "run_db", _run_db)

    with TestClient(app) as client, caplog.at_level(logging.WARNING):
        resp = client.get("/api/profiles", params={"telegramId": 1})
    assert resp.status_code == 404
    assert any(rec.levelno == logging.WARNING and "failed to fetch profile" in rec.message for rec in caplog.records)
    assert "Traceback" not in caplog.text
    engine.dispose()


def test_profiles_get_db_error_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def _get_profile(tid: int):  # noqa: ARG001
        raise RuntimeError("boom")

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "get_profile", _get_profile)

    with TestClient(app) as client:
        resp = client.get("/api/profiles", params={"telegramId": 1})
    assert resp.status_code == 500
    assert resp.json() == {"detail": "database connection failed"}


def test_profiles_get_db_connection_error_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def _get_profile(tid: int):  # noqa: ARG001
        raise ConnectionError("boom")

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "get_profile", _get_profile)

    with TestClient(app) as client:
        resp = client.get("/api/profiles", params={"telegramId": 1})
    assert resp.status_code == 503
    assert resp.json() == {"detail": "database temporarily unavailable"}


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
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=TestSession, **kwargs)

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "run_db", _run_db)
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
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=TestSession, **kwargs)

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "run_db", _run_db)
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
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=TestSession, **kwargs)

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "run_db", _run_db)
    payload = {
        "telegramId": 777,
        "icr": 0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "therapyType": "insulin",
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
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=TestSession, **kwargs)

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "run_db", _run_db)
    payload = {
        "telegramId": 777,
        "icr": 1.0,
        "cf": -1,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "therapyType": "insulin",
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
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=TestSession, **kwargs)

    from services.api.app import legacy as legacy_module

    monkeypatch.setattr(legacy_module, "run_db", _run_db)
    with TestClient(app) as client:
        payload = {
            "telegramId": 777,
            "icr": 1.0,
            "cf": 2.0,
            "target": 5.0,
            "low": 4.0,
            "high": 6.0,
            "timezone": "UTC",
            "timezoneAuto": True,
        }
        assert client.post("/api/profiles", json=payload).status_code == 200

        update = {
            "telegramId": 777,
            "icr": 3.0,
            "cf": 4.0,
            "target": 6.0,
            "low": 5.0,
            "high": 7.0,
            "timezone": "Europe/Moscow",
            "timezoneAuto": False,
        }
        assert client.post("/api/profiles", json=update).status_code == 200

        resp = client.get("/api/profiles", params={"telegramId": 777})
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Europe/Moscow"
        assert data["timezoneAuto"] is False
    engine.dispose()
