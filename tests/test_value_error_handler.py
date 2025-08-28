from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from services.api.app.main import app


@app.get("/value-error-test")
async def _value_error_endpoint() -> None:
    raise ValueError("boom")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def test_value_error_handler_returns_422(client: TestClient) -> None:
    response = client.get("/value-error-test")
    assert response.status_code == 422
    assert response.json() == {"detail": "boom"}
