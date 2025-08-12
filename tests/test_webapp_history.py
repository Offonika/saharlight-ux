import asyncio
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

import services.api.app.main as server


def test_history_persist_and_update(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(server, "HISTORY_FILE", tmp_path / "history.json")
    client = TestClient(server.app)

    rec1 = {"id": "1", "date": "2024-01-01", "time": "12:00", "type": "measurement"}
    resp = client.post("/api/history", json=rec1)
    assert resp.status_code == 200
    rec1_dump = {**rec1, "sugar": None, "carbs": None, "breadUnits": None, "insulin": None, "notes": None}
    assert json.loads(server.HISTORY_FILE.read_text(encoding="utf-8")) == [rec1_dump]

    rec1_update = {**rec1, "sugar": 5.5}
    resp = client.post("/api/history", json=rec1_update)
    assert resp.status_code == 200
    rec1_update_dump = {**rec1_dump, "sugar": 5.5}
    assert json.loads(server.HISTORY_FILE.read_text(encoding="utf-8")) == [rec1_update_dump]

    rec2 = {"id": "2", "date": "2024-01-02", "time": "13:00", "type": "meal"}
    resp = client.post("/api/history", json=rec2)
    assert resp.status_code == 200
    rec2_dump = {**rec2, "sugar": None, "carbs": None, "breadUnits": None, "insulin": None, "notes": None}
    assert json.loads(server.HISTORY_FILE.read_text(encoding="utf-8")) == [rec1_update_dump, rec2_dump]


@pytest.mark.asyncio
async def test_history_concurrent_writes(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(server, "HISTORY_FILE", tmp_path / "history.json")
    records = [
        {"id": str(i), "date": "2024-01-01", "time": "12:00", "type": "measurement"}
        for i in range(5)
    ]

    async def post_record(rec: dict[str, Any]) -> None:
        async with AsyncClient(app=server.app, base_url="http://test") as ac:
            resp = await ac.post("/api/history", json=rec)
            assert resp.status_code == 200

    await asyncio.gather(*(post_record(r) for r in records))

    dumped = json.loads(server.HISTORY_FILE.read_text(encoding="utf-8"))
    default_fields = {"sugar": None, "carbs": None, "breadUnits": None, "insulin": None, "notes": None}
    expected = [{**rec, **default_fields} for rec in records]
    assert sorted(dumped, key=lambda d: d["id"]) == expected
