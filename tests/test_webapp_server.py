"""Tests for minimal FastAPI webapp used for reminders."""

import pytest
from fastapi.testclient import TestClient

import webapp.server as server


client = TestClient(server.app)


def setup_function() -> None:
    """Reset in-memory state before each test."""
    server.REMINDERS.clear()
    server.NEXT_ID = 1


def test_reminders_post_accepts_str_and_int_ids() -> None:
    """Posting reminders with string or int IDs stores numeric IDs."""
    response = client.post("/reminders", json={"id": 5, "text": "foo"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "id": 5}
    assert server.REMINDERS[5]["id"] == 5

    response = client.post("/reminders", json={"id": "6", "text": "bar"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "id": 6}
    assert server.REMINDERS[6]["id"] == 6
    assert server.NEXT_ID == 7


@pytest.mark.parametrize("rid", [-1, "-1"])
def test_reminders_post_rejects_negative_id(rid: int | str) -> None:
    """Posting a negative ID should return a validation error."""
    response = client.post("/reminders", json={"id": rid, "text": "oops"})
    assert response.status_code == 400
    assert server.REMINDERS == {}
    assert server.NEXT_ID == 1

