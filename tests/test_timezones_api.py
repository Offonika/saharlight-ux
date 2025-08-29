from fastapi.testclient import TestClient

import services.api.app.main as server


def test_timezones_list_sorted_and_contains_utc() -> None:
    with TestClient(server.app) as client:
        resp = client.get("/api/timezones")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data == sorted(data)
    assert "UTC" in data

