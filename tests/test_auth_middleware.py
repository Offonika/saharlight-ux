import hashlib
import hmac
import json
import logging
import time
import urllib.parse

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from services.api.app.config import settings
from services.api.app.middleware.auth import AuthMiddleware, require_role
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/whoami")
    async def whoami(request: Request) -> dict[str, int | str]:
        return {"user_id": request.state.user_id, "role": request.state.role}

    return app


def test_valid_user_id_header() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/whoami", headers={"X-User-Id": "123"})
        assert response.status_code == 200
        assert response.json() == {"user_id": 123, "role": "patient"}


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
        response = client.get(
            "/admin", headers={"X-User-Id": "1", "X-Role": "patient"}
        )
        assert response.status_code == 403
    assert "Forbidden access for role 'patient'" in caplog.text


TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def test_telegram_init_data_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    app = create_app()
    init_data = build_init_data(123)
    with TestClient(app) as client:
        response = client.get("/whoami", headers={TG_INIT_DATA_HEADER: init_data})
        assert response.status_code == 200
        assert response.json() == {"user_id": 123, "role": "patient"}
