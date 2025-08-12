"""Tests for minimal FastAPI webapp used for reminders."""

import types
import pytest
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles

import services.api.app.main as server

if not server.UI_DIR.exists():
    (server.UI_DIR / "assets").mkdir(parents=True)
    (server.UI_DIR / "index.html").write_text("<html></html>", encoding="utf-8")
    (server.UI_DIR / "assets" / "index-1.css").write_text("", encoding="utf-8")
    server.app.mount(
        "/ui/assets", StaticFiles(directory=server.UI_DIR / "assets"), name="ui-assets"
    )


client = TestClient(server.app)
INDEX_HTML = (server.UI_DIR / "index.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def patch_services(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch reminder services with an in-memory store."""
    store: dict[int, dict] = {}

    async def list_reminders(telegram_id: int):
        return [
            types.SimpleNamespace(
                id=i,
                type=v["type"],
                time=v.get("time"),
                is_enabled=True,
                interval_hours=None,
            )
            for i, v in store.items() if v.get("telegram_id") == telegram_id
        ]

    async def save_reminder(data):
        rid = data.id or (max(store.keys(), default=0) + 1)
        store[rid] = {"type": data.type, "time": data.time, "telegram_id": data.telegram_id}
        return rid

    async def save_profile(data):
        return None

    monkeypatch.setattr(server.legacy, "list_reminders", list_reminders)
    monkeypatch.setattr(server.legacy, "save_reminder", save_reminder)
    monkeypatch.setattr(server.legacy, "save_profile", save_profile)


def test_root_redirects_to_ui() -> None:
    """Root URL should redirect to the UI."""
    response = client.get("/", allow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui"


def test_static_files_available() -> None:
    """Timezone page and related assets should be served as static files."""
    assert client.get("/timezone.html").status_code == 200
    css_files = list((server.UI_DIR / "assets").glob("index-*.css"))
    assert css_files, "CSS build missing"
    css_name = css_files[0].name
    assert client.get(f"/ui/assets/{css_name}").status_code == 200
    assert client.get("/telegram-init.js").status_code == 200


@pytest.mark.parametrize("path", ["/ui/reminders", "/ui/unknown/path"])
def test_spa_routes_fall_back_to_index(path: str) -> None:
    """SPA routes should return the main index.html file."""
    response = client.get(path)
    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_reminders_post_accepts_str_and_int_ids() -> None:
    """Posting reminders with string or int IDs stores numeric IDs."""
    payload = {"id": 5, "telegram_id": 1, "type": "sugar"}
    response = client.post("/api/reminders", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "id": 5}
    assert client.get("/api/reminders", params={"telegram_id": 1, "id": 5}).json()["id"] == 5

    payload = {"id": "6", "telegram_id": 1, "type": "sugar"}
    response = client.post("/api/reminders", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "id": 6}
    assert client.get("/api/reminders", params={"telegram_id": 1, "id": 6}).json()["id"] == 6

    payload = {"telegram_id": 1, "type": "sugar"}
    response = client.post("/api/reminders", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "id": 7}


