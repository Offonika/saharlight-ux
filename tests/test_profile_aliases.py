import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.app.schemas.profile import ProfileSchema


def _create_app() -> FastAPI:
    app = FastAPI()

    @app.post("/profile")
    def save_profile(data: ProfileSchema) -> ProfileSchema:  # pragma: no cover - FastAPI handles validation
        return data

    return app


def test_profile_schema_accepts_aliases_and_computes_target() -> None:
    data = ProfileSchema(
        telegramId=1,
        cf=1.0,
        targetLow=4.0,
        targetHigh=6.0,
    )
    assert data.ratio == 1.0
    assert data.low == 4.0
    assert data.high == 6.0
    assert data.target == 5.0


@pytest.mark.parametrize(
    "field,value",
    [
        ("low", {"low": 4.0, "targetLow": 5.0}),
        ("high", {"high": 6.0, "targetHigh": 7.0}),
    ],
)
def test_profiles_post_alias_mismatch_returns_422(field: str, value: dict) -> None:
    app = _create_app()
    payload = {"telegramId": 1, "cf": 1.0, **value}
    with TestClient(app) as client:
        resp = client.post("/profile", json=payload)
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["msg"] == f"Value error, {field} mismatch"
