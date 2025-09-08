from __future__ import annotations

from datetime import date
from typing import Callable, TypeVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Date, Integer, MetaData, String, Table, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.config import settings
from services.api.app.routers import metrics
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER
from tests.test_telegram_auth import TOKEN, build_init_data

T = TypeVar("T")


def setup_db() -> tuple[sessionmaker[Session], date, date]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata = MetaData()
    table = Table(
        "onboarding_metrics_daily",
        metadata,
        Column("date", Date),
        Column("variant", String),
        Column("step", String),
        Column("count", Integer),
    )
    metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    d1 = date(2024, 1, 1)
    d2 = date(2024, 1, 2)
    with engine.begin() as conn:
        conn.execute(
            table.insert(),
            [
                {"date": d1, "variant": "A", "step": "start", "count": 10},
                {"date": d1, "variant": "A", "step": "step1", "count": 8},
                {"date": d1, "variant": "A", "step": "step2", "count": 6},
                {"date": d1, "variant": "A", "step": "finish", "count": 4},
                {"date": d1, "variant": "B", "step": "start", "count": 20},
                {"date": d1, "variant": "B", "step": "step1", "count": 10},
                {"date": d1, "variant": "B", "step": "finish", "count": 5},
                {"date": d2, "variant": "A", "step": "start", "count": 5},
                {"date": d2, "variant": "A", "step": "step1", "count": 3},
                {"date": d2, "variant": "A", "step": "finish", "count": 2},
            ],
        )
    return session_local, d1, d2


def patch_run_db(
    monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]
) -> None:
    async def run_db(
        fn: Callable[[Session], T],
        *args: object,
        sessionmaker: sessionmaker[Session] = session_local,
        **kwargs: object,
    ) -> T:
        with sessionmaker() as session:
            return fn(session)

    monkeypatch.setattr(metrics, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(metrics, "run_db", run_db, raising=False)


def test_onboarding_metrics_by_day(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local, d1, d2 = setup_db()
    patch_run_db(monkeypatch, session_local)

    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data()

    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get(
            "/api/metrics/onboarding",
            params={"from": d1.isoformat(), "to": d2.isoformat()},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 200
    assert resp.json() == {
        d1.isoformat(): {
            "A": {"step1": 0.8, "step2": 0.6, "step3": 0.0, "completed": 0.4},
            "B": {"step1": 0.5, "step2": 0.0, "step3": 0.0, "completed": 0.25},
        },
        d2.isoformat(): {
            "A": {"step1": 0.6, "step2": 0.0, "step3": 0.0, "completed": 0.4},
        },
    }


def test_onboarding_metrics_variant_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local, d1, d2 = setup_db()
    patch_run_db(monkeypatch, session_local)

    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data()

    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get(
            "/api/metrics/onboarding",
            params={"from": d1.isoformat(), "to": d2.isoformat(), "variant": "A"},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 200
    assert resp.json() == {
        d1.isoformat(): {
            "A": {"step1": 0.8, "step2": 0.6, "step3": 0.0, "completed": 0.4},
        },
        d2.isoformat(): {
            "A": {"step1": 0.6, "step2": 0.0, "step3": 0.0, "completed": 0.4},
        },
    }


def test_onboarding_metrics_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local, d1, d2 = setup_db()
    patch_run_db(monkeypatch, session_local)

    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get(
            "/api/metrics/onboarding",
            params={"from": d1.isoformat(), "to": d2.isoformat()},
        )
    assert resp.status_code == 401


def test_onboarding_metrics_invalid_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local, d1, d2 = setup_db()
    patch_run_db(monkeypatch, session_local)

    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data()

    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get(
            "/api/metrics/onboarding",
            params={"from": d2.isoformat(), "to": d1.isoformat()},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 422


def test_onboarding_metrics_invalid_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local, d1, d2 = setup_db()
    patch_run_db(monkeypatch, session_local)

    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data()

    from services.api.app.main import app

    with TestClient(app) as client:
        resp = client.get(
            "/api/metrics/onboarding",
            params={"from": d1.isoformat(), "to": d2.isoformat(), "variant": "bad!"},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 422
