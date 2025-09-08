import logging
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
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


def test_profiles_post_user_missing_returns_404(
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
    assert resp.status_code == 404
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

    with TestSession() as session:
        session.add(db.User(telegram_id=777, thread_id="t"))
        session.commit()

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


def test_profiles_post_preserves_unspecified_fields(
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

    with TestSession() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.commit()

    with TestClient(app) as client:
        payload = {
            "telegramId": 1,
            "icr": 1.0,
            "cf": 1.0,
            "target": 5.0,
            "low": 4.0,
            "high": 6.0,
            "dia": 6.0,
            "preBolus": 10,
            "roundStep": 0.5,
            "carbUnits": "g",
            "gramsPerXe": 12.0,
            "rapidInsulinType": "aspart",
            "maxBolus": 15.0,
            "afterMealMinutes": 90,
        }
        assert client.post("/api/profiles", json=payload).status_code == 200

        update = {
            "telegramId": 1,
            "icr": 2.0,
            "cf": 1.5,
            "target": 5.5,
            "low": 4.5,
            "high": 6.5,
        }
        assert client.post("/api/profiles", json=update).status_code == 200

        resp = client.get("/api/profiles", params={"telegramId": 1})
        data = resp.json()
        assert data["dia"] == 6.0
        assert data["preBolus"] == 10
        assert data["roundStep"] == 0.5
        assert data["carbUnits"] == "g"
        assert data["gramsPerXe"] == 12.0
        assert data["rapidInsulinType"] == "aspart"
        assert data["maxBolus"] == 15.0
        assert data["afterMealMinutes"] == 90
    engine.dispose()


def test_profiles_post_partial_update_multiple_fields(
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

    with TestSession() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.commit()

    with TestClient(app) as client:
        base_payload = {
            "telegramId": 1,
            "icr": 1.0,
            "cf": 1.0,
            "target": 5.0,
            "low": 4.0,
            "high": 6.0,
        }
        assert client.post("/api/profiles", json=base_payload).status_code == 200

        update = {
            "telegramId": 1,
            "target": 5.0,
            "low": 4.0,
            "high": 6.0,
            "dia": 7.0,
            "preBolus": 5,
            "roundStep": 1.0,
        }
        assert client.post("/api/profiles", json=update).status_code == 200

        resp = client.get("/api/profiles", params={"telegramId": 1})
        data = resp.json()
        assert data["dia"] == 7.0
        assert data["preBolus"] == 5
        assert data["roundStep"] == 1.0
    engine.dispose()


def test_profiles_post_call_order_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def setup_client() -> tuple[TestClient, Engine]:
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
        with TestSession() as session:
            session.add(db.User(telegram_id=1, thread_id="t"))
            session.commit()
        client = TestClient(app)
        return client, engine

    base = {
        "telegramId": 1,
        "icr": 1.0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
    }
    adv = {
        "telegramId": 1,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "dia": 8.0,
        "preBolus": 12,
    }

    client1, engine1 = setup_client()
    assert client1.post("/api/profiles", json=base).status_code == 200
    assert client1.post("/api/profiles", json=adv).status_code == 200
    data1 = client1.get("/api/profiles", params={"telegramId": 1}).json()
    engine1.dispose()

    client2, engine2 = setup_client()
    assert client2.post("/api/profiles", json=adv).status_code == 200
    assert client2.post("/api/profiles", json=base).status_code == 200
    data2 = client2.get("/api/profiles", params={"telegramId": 1}).json()
    engine2.dispose()

    assert data1 == data2
