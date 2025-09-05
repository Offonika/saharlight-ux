from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from services.api.app.main import app
from services.api.app.routers.webapp import UI_DIR


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def _index_html() -> str:
    return (UI_DIR / "index.html").read_text()


def test_ui_root_returns_index(client: TestClient) -> None:
    expected = _index_html()
    response = client.get("/ui")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.text == expected


def test_ui_any_path_returns_index(client: TestClient) -> None:
    expected = _index_html()
    response = client.get("/ui/anything")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.text == expected


def test_ui_existing_file_returns_file(client: TestClient) -> None:
    file_path = UI_DIR / "real-file.js"
    if not file_path.is_file():
        pytest.skip("real-file.js missing")
    expected = file_path.read_text()
    response = client.get("/ui/real-file.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.text == expected
