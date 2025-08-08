from pathlib import Path

from fastapi.testclient import TestClient

import webapp.server as server


def test_timezone_persist_and_validate(monkeypatch, tmp_path: Path) -> None:
    tz_path = tmp_path / "tz.txt"
    monkeypatch.setattr(server, "TIMEZONE_FILE", tz_path)
    client = TestClient(server.app)

    # valid timezone
    resp = client.post("/api/timezone", json={"tz": "Europe/Moscow"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert tz_path.read_text(encoding="utf-8") == "Europe/Moscow"

    # missing tz
    resp = client.post("/api/timezone", json={})
    assert resp.status_code == 400

    # invalid tz value
    resp = client.post("/api/timezone", json={"tz": "Invalid/Zone"})
    assert resp.status_code == 400

    # invalid json
    resp = client.post(
        "/api/timezone", data="not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400


def test_timezone_storage_error(monkeypatch) -> None:
    class FailingPath:
        def open(self, *args, **kwargs):
            raise OSError("no space")

    monkeypatch.setattr(server, "TIMEZONE_FILE", FailingPath())
    client = TestClient(server.app)
    resp = client.post("/api/timezone", json={"tz": "Europe/Moscow"})
    assert resp.status_code == 500
    assert resp.json() == {"detail": "storage error"}
