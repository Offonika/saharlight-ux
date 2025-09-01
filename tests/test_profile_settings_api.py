import pytest
from fastapi.testclient import TestClient

import services.api.app.main as server


def auth_override() -> dict[str, int]:
    return {"id": 1}


@pytest.fixture(autouse=True)
def override_auth() -> None:
    server.app.dependency_overrides[server.require_tg_user] = auth_override
    yield
    server.app.dependency_overrides.clear()


def test_profile_settings_serialization() -> None:
    with TestClient(server.app) as client:
        resp = client.get("/api/profile/settings")
    assert resp.status_code == 200
    assert resp.json() == {"gramsPerXe": 12, "roundStep": 1.0, "maxBolus": 25.0}


@pytest.mark.parametrize(
    "payload",
    [
        {"gramsPerXe": 11},
        {"roundStep": 0.7},
        {"maxBolus": 30.0},
        {"maxBolus": 0.4},
    ],
)
def test_profile_settings_validation(payload: dict[str, float]) -> None:
    with TestClient(server.app) as client:
        resp = client.patch("/api/profile/settings", json=payload)
    assert resp.status_code == 422


def test_profile_settings_patch_updates() -> None:
    with TestClient(server.app) as client:
        patch = {"gramsPerXe": 10, "roundStep": 0.5, "maxBolus": 20.0}
        resp = client.patch("/api/profile/settings", json=patch)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        resp = client.get("/api/profile/settings")
    assert resp.json() == patch
