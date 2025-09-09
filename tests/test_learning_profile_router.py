from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.main import app
from services.api.app.diabetes.services.db import Base, User
from services.api.app.diabetes.models_learning import LearningUserProfile
from services.api.app.telegram_auth import check_token
import services.api.app.assistant.repositories.learning_profile as repo


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[User.__table__, LearningUserProfile.__table__])
    return sessionmaker(bind=engine, class_=Session)


def make_client(
    monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]
) -> TestClient:
    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(repo, "run_db", run_db, raising=False)
    monkeypatch.setattr(repo, "SessionLocal", session_local, raising=False)
    app.dependency_overrides[check_token] = lambda: {"id": 1}
    return TestClient(app)


def teardown_client() -> None:
    app.dependency_overrides.clear()


def add_user(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()


@pytest.mark.asyncio
async def test_get_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local)
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/learning-profile")
    assert resp.status_code == 200
    assert resp.json() == {}
    teardown_client()


@pytest.mark.asyncio
async def test_patch_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local)
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.patch(
            "/api/learning-profile",
            json={
                "age_group": "adult",
                "learning_level": "novice",
                "diabetes_type": "T1",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "age_group": "adult",
            "learning_level": "novice",
            "diabetes_type": "T1",
        }
        resp2 = client.get("/api/learning-profile")
    assert resp2.json() == {
        "age_group": "adult",
        "learning_level": "novice",
        "diabetes_type": "T1",
    }
    teardown_client()
