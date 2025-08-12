from fastapi.testclient import TestClient

import services.api.app.main as server


def test_timezone_persist_and_validate(tmp_path, monkeypatch) -> None:
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
