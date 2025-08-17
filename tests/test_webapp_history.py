import asyncio
import hashlib
import hmac
import json
import time
import urllib.parse

from typing import Any, Callable, cast

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.diabetes.services import db

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    return SessionLocal


def test_history_auth_required(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_db(monkeypatch)
    client = TestClient(server.app)
    rec = {"id": "1", "date": "2024-01-01", "time": "12:00", "type": "measurement"}
    assert client.post("/api/history", json=rec).status_code == 401
    assert client.get("/api/history").status_code == 401
    assert client.delete("/api/history/1").status_code == 401


def test_history_persist_and_update(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    monkeypatch.setenv("TELEGRAM_TOKEN", TOKEN)
    client = TestClient(server.app)
    headers1 = {"X-Telegram-Init-Data": build_init_data(1)}
    headers2 = {"X-Telegram-Init-Data": build_init_data(2)}

    rec1 = {"id": "1", "date": "2024-01-01", "time": "12:00", "type": "measurement"}
    resp = client.post("/api/history", json=rec1, headers=headers1)
    assert resp.status_code == 200

    with Session() as session:
        stored = session.get(db.HistoryRecord, "1")
        assert stored is not None
        assert stored.date == "2024-01-01"
        assert stored.telegram_id == 1

    rec1_update = {**rec1, "sugar": 5.5}
    resp = client.post("/api/history", json=rec1_update, headers=headers1)
    assert resp.status_code == 200

    with Session() as session:
        stored = session.get(db.HistoryRecord, "1")
        assert stored is not None
        assert stored.sugar == 5.5

    rec2 = {"id": "2", "date": "2024-01-02", "time": "13:00", "type": "meal"}
    resp = client.post("/api/history", json=rec2, headers=headers1)
    assert resp.status_code == 200

    rec3 = {"id": "3", "date": "2024-01-03", "time": "14:00", "type": "meal"}
    resp = client.post("/api/history", json=rec3, headers=headers2)
    assert resp.status_code == 200

    resp = client.get("/api/history", headers=headers1)
    assert [r["id"] for r in resp.json()] == ["1", "2"]

    resp = client.get("/api/history", headers=headers2)
    assert [r["id"] for r in resp.json()] == ["3"]

    resp = client.delete("/api/history/1", headers=headers2)
    assert resp.status_code == 403

    resp = client.delete("/api/history/1", headers=headers1)
    assert resp.status_code == 200

    resp = client.get("/api/history", headers=headers1)
    assert [r["id"] for r in resp.json()] == ["2"]


@pytest.mark.asyncio
async def test_history_concurrent_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    monkeypatch.setenv("TELEGRAM_TOKEN", TOKEN)
    headers = {"X-Telegram-Init-Data": build_init_data(1)}
    records = [
        {"id": str(i), "date": "2024-01-01", "time": "12:00", "type": "measurement"}
        for i in range(5)
    ]

    async def post_record(rec: dict[str, Any]) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=cast(Any, server.app)), base_url="http://test"
        ) as ac:
            resp = await ac.post("/api/history", json=rec, headers=headers)
            assert resp.status_code == 200

    await asyncio.gather(*(post_record(r) for r in records))

    with Session() as session:
        stored = session.query(db.HistoryRecord).filter_by(telegram_id=1).all()
        assert sorted([r.id for r in stored]) == [r["id"] for r in records]
