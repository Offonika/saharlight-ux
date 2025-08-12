import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

import services.api.app.main as server


def test_timezone_persist_and_validate(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(server, "TIMEZONE_FILE", tmp_path / "timezone.txt")
    client = TestClient(server.app)

    resp = client.put("/timezone", json={"tz": "Europe/Moscow"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert server.TIMEZONE_FILE.read_text(encoding="utf-8") == "Europe/Moscow"

    resp = client.get("/timezone")
    assert resp.status_code == 200
    assert resp.json() == {"tz": "Europe/Moscow"}

    resp = client.put("/timezone", json={})
    assert resp.status_code == 422

    resp = client.put("/timezone", json={"tz": "Invalid/Zone"})
    assert resp.status_code == 400

    resp = client.put(
        "/timezone", content=b"not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code in {400, 422}


def test_timezone_partial_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(server, "TIMEZONE_FILE", tmp_path / "timezone.txt")
    server.TIMEZONE_FILE.write_text("Europe/Mosc", encoding="utf-8")
    client = TestClient(server.app)
    resp = client.get("/timezone")
    assert resp.status_code == 500


def test_timezone_concurrent_writes(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(server, "TIMEZONE_FILE", tmp_path / "timezone.txt")
    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo", "Europe/Paris"]

    def write_tz(tz: str) -> None:
        with TestClient(server.app) as c:
            resp = c.put("/timezone", json={"tz": tz})
            assert resp.status_code == 200

    with ThreadPoolExecutor(max_workers=len(timezones)) as exc:
        list(exc.map(write_tz, timezones))

    final_value = server.TIMEZONE_FILE.read_text(encoding="utf-8").strip()
    assert final_value in timezones

    client = TestClient(server.app)
    resp = client.get("/timezone")
    assert resp.status_code == 200
    assert resp.json() == {"tz": final_value}


@pytest.mark.asyncio
async def test_timezone_async_writes(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(server, "TIMEZONE_FILE", tmp_path / "timezone.txt")
    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo", "Europe/Paris"]

    async def write_tz(tz: str) -> None:
        async with AsyncClient(app=server.app, base_url="http://test") as ac:
            resp = await ac.put("/timezone", json={"tz": tz})
            assert resp.status_code == 200

    await asyncio.gather(*(write_tz(tz) for tz in timezones))

    final_value = server.TIMEZONE_FILE.read_text(encoding="utf-8").strip()
    assert final_value in timezones

    async with AsyncClient(app=server.app, base_url="http://test") as ac:
        resp = await ac.get("/timezone")
        assert resp.status_code == 200
        assert resp.json() == {"tz": final_value}
