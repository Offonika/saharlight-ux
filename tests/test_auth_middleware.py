import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
import pytest

from services.api.app.middleware.auth import AuthMiddleware, require_role


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/whoami")
    async def whoami(request: Request) -> dict[str, int]:
        return {"user_id": request.state.user_id}

    return app


def test_valid_user_id_header() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/whoami", headers={"X-User-Id": "123"})
        assert response.status_code == 200
        assert response.json() == {"user_id": 123}


def test_missing_user_id_header(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app()
    with TestClient(app) as client:
        caplog.set_level(logging.WARNING, logger="services.api.app.middleware.auth")
        with pytest.raises(HTTPException) as exc_info:
            client.get("/whoami")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "invalid user id"
    assert "Missing X-User-Id" in caplog.text


def test_invalid_user_id_header(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app()
    with TestClient(app) as client:
        caplog.set_level(logging.WARNING, logger="services.api.app.middleware.auth")
        with pytest.raises(HTTPException) as exc_info:
            client.get("/whoami", headers={"X-User-Id": "abc"})
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "invalid user id"
    assert "Invalid X-User-Id" in caplog.text


def test_invalid_role_header_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()
    with TestClient(app) as client:
        caplog.set_level(logging.WARNING, logger="services.api.app.middleware.auth")
        with pytest.raises(HTTPException) as exc_info:
            client.get(
                "/whoami",
                headers={"X-User-Id": "1", "X-Role": "hacker"},
            )
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "invalid role"
    assert "Invalid X-Role" in caplog.text


def test_require_role_logs_attempt(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/admin", dependencies=[Depends(require_role("superadmin"))])
    async def admin() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        caplog.set_level(logging.WARNING, logger="services.api.app.middleware.auth")
        response = client.get("/admin", headers={"X-User-Id": "1", "X-Role": "patient"})
        assert response.status_code == 403
    assert "Forbidden access for user 1 with role 'patient'" in caplog.text
