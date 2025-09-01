import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as main
import services.api.app.diabetes.services.db as db
import services.api.app.legacy as legacy
from services.api.app.diabetes.services.db import Base, User


def _build_app(session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    app = FastAPI()
    app.include_router(main.api_router, prefix="/api")
    app.dependency_overrides[main.require_tg_user] = lambda: {"id": 1}

    monkeypatch.setattr(db, "SessionLocal", session_factory, raising=False)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=session_factory, **kwargs)

    monkeypatch.setattr(main, "run_db", _run_db)
    monkeypatch.setattr(legacy, "run_db", _run_db)
    return app


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = _build_app(session_factory, monkeypatch)
    return TestClient(app)


def test_patch_serialization_and_persistence(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    resp = client.patch(
        "/api/profile",
        json={"round_step": 1.0, "grams_per_xe": 10, "dia": 7},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["roundStep"] == 1.0
    assert data["gramsPerXe"] == 10
    assert data["dia"] == 7

    with session_factory() as session:
        user = session.get(User, 1)
        assert user is not None
        assert user.round_step == 1.0
        assert user.grams_per_xe == 10
        assert user.dia == 7


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"gramsPerXe": 11}, "gramsPerXe must be 10 or 12"),
        ({"roundStep": 0.3}, "roundStep must be one of 0.5 or 1.0"),
        ({"dia": 25}, "dia must be between 1 and 24 hours"),
    ],
)
def test_patch_validation_errors(client: TestClient, payload: dict[str, float], message: str) -> None:
    resp = client.patch("/api/profile", json=payload)
    assert resp.status_code == 422
    assert message in resp.text
