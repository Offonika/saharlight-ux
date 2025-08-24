from fastapi.testclient import TestClient
from services.api.app.main import app


def test_reminders_page_smoke() -> None:
    with TestClient(app) as client:
        resp = client.get("/ui/reminders")
        assert resp.status_code == 200
        assert "<html" in resp.text.lower()
