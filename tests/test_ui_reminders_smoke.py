from fastapi.testclient import TestClient

from services.api.app import config
from services.api.app.main import app


def test_reminders_page_smoke() -> None:
    with TestClient(app) as client:
        base = config.get_settings().ui_base_url.rstrip("/")
        resp = client.get(f"{base}/reminders")
        assert resp.status_code == 200
        assert "<html" in resp.text.lower()


def test_reminders_new_page_smoke() -> None:
    with TestClient(app) as client:
        base = config.get_settings().ui_base_url.rstrip("/")
        resp = client.get(f"{base}/reminders/new")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "<html" in resp.text.lower()
