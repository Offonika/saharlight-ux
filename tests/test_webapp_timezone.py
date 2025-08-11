
from fastapi.testclient import TestClient

import backend.main as server


def test_timezone_persist_and_validate(monkeypatch) -> None:
    stored: dict[int, str] = {}

    async def fake_set_timezone(tid: int, tz: str) -> None:
        stored[tid] = tz

    monkeypatch.setattr(server, "set_timezone", fake_set_timezone)
    client = TestClient(server.app)

    resp = client.post("/api/timezone", json={"telegram_id": 1, "tz": "Europe/Moscow"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert stored[1] == "Europe/Moscow"

    resp = client.post("/api/timezone", json={"telegram_id": 1})
    assert resp.status_code == 422

    resp = client.post("/api/timezone", json={"telegram_id": 1, "tz": "Invalid/Zone"})
    assert resp.status_code == 400

    resp = client.post(
        "/api/timezone", content=b"not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code in {400, 422}
