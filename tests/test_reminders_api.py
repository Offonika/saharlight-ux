import pytest
from collections.abc import Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import cast

from services.api.app.diabetes.services.db import Base, Reminder, User
from services.api.app.routers.reminders import router
from services.api.app.services import reminders
from services.api.app.telegram_auth import require_tg_user


@pytest.fixture()
def session_factory() -> Generator[sessionmaker, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.fixture()
def client(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker
) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
    with TestClient(app) as test_client:
        yield test_client


def test_empty_returns_200(client: TestClient, session_factory: sessionmaker) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == []


def test_nonempty_returns_list(
    client: TestClient, session_factory: sessionmaker
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time="08:00",
                interval_hours=3,
            )
        )
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "telegramId": 1,
            "id": 1,
            "type": "sugar",
            "title": "sugar",
            "time": "08:00",
            "intervalHours": 3,
            "minutesAfter": None,
            "isEnabled": True,
            "orgId": None,
        }
    ]


def test_invalid_telegram_id_returns_empty_list(client: TestClient) -> None:
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.get("/api/reminders", params={"telegramId": 2})
    assert resp.status_code == 200
    assert resp.json() == []


def test_mismatched_telegram_id_returns_404(client: TestClient) -> None:
    resp = client.get("/api/reminders", params={"telegramId": 2})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "reminder not found"}


def test_patch_updates_reminder(
    client: TestClient, session_factory: sessionmaker
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time="08:00",
                interval_hours=3,
            )
        )
        session.commit()
    resp = client.patch(
        "/api/reminders",
        json={
            "telegramId": 1,
            "id": 1,
            "type": "sugar",
            "time": "09:00",
            "intervalHours": 3,
            "isEnabled": True,
        },
    )
    assert resp.status_code == 200
    with session_factory() as session:
        rem = session.get(Reminder, 1)
        assert rem is not None
        assert rem.time == "09:00"


def test_delete_reminder(client: TestClient, session_factory: sessionmaker) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()
    resp = client.delete(
        "/api/reminders", params={"telegramId": 1, "id": 1}
    )
    assert resp.status_code == 200
    with session_factory() as session:
        assert session.get(Reminder, 1) is None
