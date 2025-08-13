import asyncio
from concurrent.futures import ThreadPoolExecutor

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
        return await db.run_db(fn, *args, sessionmaker=Session, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    return Session


def test_timezone_persist_and_validate(monkeypatch) -> None:
    Session = setup_db(monkeypatch)
    client = TestClient(server.app)

    resp = client.put("/timezone", json={"tz": "Europe/Moscow"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    resp = client.get("/timezone")
    assert resp.status_code == 200
    assert resp.json() == {"tz": "Europe/Moscow"}

    with Session() as session:
        tz_row = session.get(db.Timezone, 1)
        assert tz_row.tz == "Europe/Moscow"

    resp = client.put("/timezone", json={})
    assert resp.status_code == 422

    resp = client.put("/timezone", json={"tz": "Invalid/Zone"})
    assert resp.status_code == 400

    resp = client.put(
        "/timezone", content=b"not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code in {400, 422}


def test_timezone_partial_file(monkeypatch) -> None:
    Session = setup_db(monkeypatch)
    with Session() as session:
        session.add(db.Timezone(id=1, tz="Europe/Mosc"))
        session.commit()

    client = TestClient(server.app)
    resp = client.get("/timezone")
    assert resp.status_code == 500


def test_timezone_concurrent_writes(monkeypatch) -> None:
    Session = setup_db(monkeypatch)
    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo", "Europe/Paris"]

    def write_tz(tz: str) -> None:
        with TestClient(server.app) as c:
            resp = c.put("/timezone", json={"tz": tz})
            assert resp.status_code == 200

    with ThreadPoolExecutor(max_workers=len(timezones)) as exc:
        list(exc.map(write_tz, timezones))

    with Session() as session:
        tz_row = session.get(db.Timezone, 1)
        assert tz_row.tz in timezones

    client = TestClient(server.app)
    resp = client.get("/timezone")
    assert resp.status_code == 200
    assert resp.json() == {"tz": tz_row.tz}


@pytest.mark.asyncio
async def test_timezone_async_writes(monkeypatch) -> None:
    Session = setup_db(monkeypatch)
    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo", "Europe/Paris"]

    async def write_tz(tz: str) -> None:
        async with AsyncClient(app=server.app, base_url="http://test") as ac:
            resp = await ac.put("/timezone", json={"tz": tz})
            assert resp.status_code == 200

    await asyncio.gather(*(write_tz(tz) for tz in timezones))

    with Session() as session:
        tz_row = session.get(db.Timezone, 1)
        assert tz_row.tz in timezones

    async with AsyncClient(app=server.app, base_url="http://test") as ac:
        resp = await ac.get("/timezone")
        assert resp.status_code == 200
        assert resp.json() == {"tz": tz_row.tz}

