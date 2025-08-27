import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
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
        return await db.run_db(
            lambda session: fn(session, *args, **kwargs), sessionmaker=Session
        )

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    return Session


def test_history_persist_and_update(monkeypatch) -> None:
    Session = setup_db(monkeypatch)
    client = TestClient(server.app)

    rec1 = {"id": "1", "date": "2024-01-01", "time": "12:00", "type": "measurement"}
    resp = client.post("/api/history", json=rec1)
    assert resp.status_code == 200

    with Session() as session:
        stored = session.get(db.HistoryRecord, "1")
        assert stored is not None
        assert stored.date == "2024-01-01"
        assert stored.sugar is None

    rec1_update = {**rec1, "sugar": 5.5}
    resp = client.post("/api/history", json=rec1_update)
    assert resp.status_code == 200

    with Session() as session:
        stored = session.get(db.HistoryRecord, "1")
        assert stored.sugar == 5.5

    rec2 = {"id": "2", "date": "2024-01-02", "time": "13:00", "type": "meal"}
    resp = client.post("/api/history", json=rec2)
    assert resp.status_code == 200

    with Session() as session:
        records = session.query(db.HistoryRecord).order_by(db.HistoryRecord.id).all()
        assert [r.id for r in records] == ["1", "2"]


@pytest.mark.asyncio
async def test_history_concurrent_writes(monkeypatch) -> None:
    Session = setup_db(monkeypatch)
    records = [
        {"id": str(i), "date": "2024-01-01", "time": "12:00", "type": "measurement"}
        for i in range(5)
    ]

    async def post_record(rec: dict) -> None:
        async with AsyncClient(app=server.app, base_url="http://test") as ac:
            resp = await ac.post("/api/history", json=rec)
            assert resp.status_code == 200

    await asyncio.gather(*(post_record(r) for r in records))

    with Session() as session:
        stored = session.query(db.HistoryRecord).all()
        assert sorted([r.id for r in stored]) == [r["id"] for r in records]

