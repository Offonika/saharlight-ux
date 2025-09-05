import asyncio
import hashlib
import hmac
import json
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, cast

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.config import settings
from services.api.app.diabetes.services import db
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


@pytest.fixture
def auth_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    return {TG_INIT_DATA_HEADER: build_init_data()}


def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    # Ensure application code uses the in-memory sessionmaker
    monkeypatch.setattr(db, "SessionLocal", SessionLocal)

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    return SessionLocal


def test_timezone_persist_and_validate(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    Session = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.put(
            "/api/timezone", json={"tz": "Europe/Moscow"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        resp = client.get("/api/timezone", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"tz": "Europe/Moscow"}

        with Session() as session:
            tz_row = session.get(db.Timezone, 1)
            assert tz_row is not None
            assert tz_row.tz == "Europe/Moscow"

        resp = client.put("/api/timezone", json={}, headers=auth_headers)
        assert resp.status_code == 422

        resp = client.put(
            "/api/timezone", json={"tz": "Invalid/Zone"}, headers=auth_headers
        )
        assert resp.status_code == 400

        resp = client.put(
            "/api/timezone",
            content=b"not json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code in {400, 422}


def test_timezone_partial_file(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    Session = setup_db(monkeypatch)
    with Session() as session:
        session.add(db.Timezone(id=1, tz="Europe/Mosc"))
        session.commit()

    with TestClient(server.app) as client:
        resp = client.get("/api/timezone", headers=auth_headers)
        assert resp.status_code == 400


def test_timezone_concurrent_writes(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    Session = setup_db(monkeypatch)
    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo", "Europe/Paris"]

    headers = auth_headers

    def write_tz(tz: str) -> None:
        with TestClient(server.app) as c:
            resp = c.put("/api/timezone", json={"tz": tz}, headers=headers.copy())
            assert resp.status_code == 200

    with ThreadPoolExecutor(max_workers=len(timezones)) as exc:
        list(exc.map(write_tz, timezones))

    with Session() as session:
        tz_row = session.get(db.Timezone, 1)
        assert tz_row is not None
        assert tz_row.tz in timezones
        tz_value = tz_row.tz

    with TestClient(server.app) as client:
        resp = client.get("/api/timezone", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"tz": tz_value}


@pytest.mark.asyncio
async def test_timezone_async_writes(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    Session = setup_db(monkeypatch)
    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo", "Europe/Paris"]

    headers = auth_headers

    async def write_tz(tz: str) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=cast(Any, server.app)), base_url="http://test"
        ) as ac:
            resp = await ac.put("/api/timezone", json={"tz": tz}, headers=headers)
            assert resp.status_code == 200

    await asyncio.gather(*(write_tz(tz) for tz in timezones))

    with Session() as session:
        tz_row = session.get(db.Timezone, 1)
        assert tz_row is not None
        assert tz_row.tz in timezones
        tz_value = tz_row.tz

    async with AsyncClient(
        transport=ASGITransport(app=cast(Any, server.app)), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/timezone", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"tz": tz_value}


def test_timezone_requires_header() -> None:
    with TestClient(server.app) as client:
        assert client.get("/api/timezone").status_code == 401
        assert (
            client.put("/api/timezone", json={"tz": "Europe/Moscow"}).status_code == 401
        )
