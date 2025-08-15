import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from services.api.app.middleware.auth import AuthMiddleware


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/whoami")
    async def whoami(request: Request) -> dict[str, int]:
        return {"user_id": request.state.user_id}

    return app


def test_valid_user_id_header() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/whoami", headers={"X-User-Id": "123"})
    assert response.status_code == 200
    assert response.json() == {"user_id": 123}


def test_missing_user_id_header() -> None:
    app = create_app()
    client = TestClient(app)
    with pytest.raises(HTTPException) as exc_info:
        client.get("/whoami")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "invalid user id"


def test_invalid_user_id_header() -> None:
    app = create_app()
    client = TestClient(app)
    with pytest.raises(HTTPException) as exc_info:
        client.get("/whoami", headers={"X-User-Id": "abc"})
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "invalid user id"
