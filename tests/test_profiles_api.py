from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.app.legacy import router


def test_profiles_get_requires_telegram_id() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    resp = client.get("/api/profiles")
    assert resp.status_code == 422

