import json
from fastapi.testclient import TestClient
import services.api.app.main as server


def test_history_persist_and_update(tmp_path, monkeypatch) -> None:
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
