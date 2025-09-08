import asyncio
import hashlib
import hmac
import json
import datetime
import time
import urllib.parse
from typing import Any, Callable, ContextManager, cast

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.config import settings
from services.api.app.diabetes.services import db
from services.api.app.diabetes.services.db import SessionMaker
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def setup_db(monkeypatch: pytest.MonkeyPatch) -> SessionMaker[SASession]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal: SessionMaker[SASession] = sessionmaker(bind=engine, class_=SASession)
    db.Base.metadata.create_all(bind=engine)

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    with SessionLocal() as session:
        session.add_all(
            [
                db.User(telegram_id=1, thread_id="t"),
                db.User(telegram_id=2, thread_id="t"),
            ]
        )
        session.commit()
    return SessionLocal


def test_history_auth_required(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    with TestClient(server.app) as client:
        rec = {"id": "1", "date": "2024-01-01", "time": "12:00", "type": "measurement"}
        assert client.post("/api/history", json=rec).status_code == 401
        assert client.get("/api/history").status_code == 401
        assert client.delete("/api/history/1").status_code == 401


def test_history_invalid_date_time(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    headers = {TG_INIT_DATA_HEADER: build_init_data(1)}
    with TestClient(server.app) as client:
        bad_date = {
            "id": "1",
            "date": "2024-13-01",
            "time": "12:00",
            "type": "measurement",
        }
        resp = client.post("/api/history", json=bad_date, headers=headers)
        assert resp.status_code == 422
        bad_time = {
            "id": "1",
            "date": "2024-01-01",
            "time": "24:00",
            "type": "measurement",
        }
        resp = client.post("/api/history", json=bad_time, headers=headers)
        assert resp.status_code == 422

        bad_time_seconds = {
            "id": "2",
            "date": "2024-01-01",
            "time": "12:00:00",
            "type": "measurement",
        }
        resp = client.post("/api/history", json=bad_time_seconds, headers=headers)
        assert resp.status_code == 422


def test_history_persist_and_update(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    headers1 = {TG_INIT_DATA_HEADER: build_init_data(1)}
    headers2 = {TG_INIT_DATA_HEADER: build_init_data(2)}
    with TestClient(server.app) as client:
        rec1 = {
            "id": "1",
            "date": "2024-01-01",
            "time": "12:00",
            "type": "measurement",
        }
        resp = client.post("/api/history", json=rec1, headers=headers1)
        assert resp.status_code == 200

        with cast(ContextManager[SASession], Session()) as session:
            stored = cast(Any, session).get(db.HistoryRecord, "1")
            assert stored is not None
            assert stored.date == datetime.date(2024, 1, 1)
            assert stored.time == datetime.time(12, 0)
            assert stored.telegram_id == 1

        rec1_update = {**rec1, "sugar": 5.5}
        resp = client.post("/api/history", json=rec1_update, headers=headers1)
        assert resp.status_code == 200

        with cast(ContextManager[SASession], Session()) as session:
            stored = cast(Any, session).get(db.HistoryRecord, "1")
            assert stored is not None
            assert stored.sugar == 5.5

        rec2 = {"id": "2", "date": "2024-01-02", "time": "13:00", "type": "meal"}
        resp = client.post("/api/history", json=rec2, headers=headers1)
        assert resp.status_code == 200

        rec3 = {"id": "3", "date": "2024-01-03", "time": "14:00", "type": "meal"}
        resp = client.post("/api/history", json=rec3, headers=headers2)
        assert resp.status_code == 200

        resp = client.get("/api/history", headers=headers1)
        body = resp.json()
        assert [r["id"] for r in body] == ["2", "1"]
        assert body[0]["time"] == "13:00"
        assert body[1]["time"] == "12:00"

        resp = client.get("/api/history?limit=1", headers=headers1)
        assert [r["id"] for r in resp.json()] == ["2"]

        resp = client.get("/api/history", headers=headers2)
        assert [r["id"] for r in resp.json()] == ["3"]

        resp = client.delete("/api/history/1", headers=headers2)
        assert resp.status_code == 403

        resp = client.delete("/api/history/1", headers=headers1)
        assert resp.status_code == 200

        resp = client.get("/api/history", headers=headers1)
        assert [r["id"] for r in resp.json()] == ["2"]


def test_history_invalid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    headers = {TG_INIT_DATA_HEADER: build_init_data(1)}
    with cast(ContextManager[SASession], Session()) as session:
        session.add(
            db.HistoryRecord(
                id="1",
                telegram_id=1,
                date=datetime.date(2024, 1, 1),
                time=datetime.time(12, 0),
                type="invalid",
            )
        )
        session.add(
            db.HistoryRecord(
                id="2",
                telegram_id=1,
                date=datetime.date(2024, 1, 2),
                time=datetime.time(13, 0),
                type="meal",
            )
        )
        session.commit()

    with TestClient(server.app) as client:
        resp = client.get("/api/history", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert [r["id"] for r in body] == ["2"]


@pytest.mark.asyncio
async def test_history_concurrent_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    headers = {TG_INIT_DATA_HEADER: build_init_data(1)}
    records = [{"id": str(i), "date": "2024-01-01", "time": "12:00", "type": "measurement"} for i in range(5)]

    async def post_record(rec: dict[str, Any]) -> None:
        async with AsyncClient(transport=ASGITransport(app=cast(Any, server.app)), base_url="http://test") as ac:
            resp = await ac.post("/api/history", json=rec, headers=headers)
            assert resp.status_code == 200

    await asyncio.gather(*(post_record(r) for r in records))

    with cast(ContextManager[SASession], Session()) as session:
        stored = session.query(db.HistoryRecord).filter_by(telegram_id=1).all()
        assert sorted([r.id for r in stored]) == [r["id"] for r in records]
