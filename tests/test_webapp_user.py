import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.diabetes.services import db


def setup_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Session = sessionmaker(bind=engine)
    db.Base.metadata.create_all(bind=engine)

    async def run_db_wrapper(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=Session, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    return Session


def test_create_user(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    client = TestClient(server.app)

    resp = client.post("/api/user", json={"telegram_id": 42})
    assert resp.status_code == 200

    with Session() as session:
        user = session.get(db.User, 42)
        assert user is not None
        assert user.thread_id == "webapp"
