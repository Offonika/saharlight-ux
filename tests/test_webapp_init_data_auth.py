import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
import importlib

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from telegram import Update
from telegram.ext import CallbackContext

import services.api.rest_client as rest_client
import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.diabetes.handlers.reminder_handlers as reminder
from services.api.app.config import settings
import services.api.app.routers.profile as profile_router

profile_conv = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


class DummyMessage:
    def __init__(self, data: str) -> None:
        self.web_app_data = SimpleNamespace(data=data)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.replies.append(text)


class DummyResponse:
    def raise_for_status(self) -> None:
        return

    def json(self) -> dict[str, object]:
        return {}


class DummyClient:
    def __init__(self, capture: dict[str, object]) -> None:
        self.capture = capture

    async def __aenter__(self) -> "DummyClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        return None

    async def get(
        self, url: str, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        self.capture["headers"] = headers
        return DummyResponse()


class Settings:
    api_url = "http://example"
    internal_api_key: str | None = None


async def _assert_header(
    ctx: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rest_client, "get_settings", lambda: Settings())
    captured: dict[str, object] = {}
    monkeypatch.setattr(httpx, "AsyncClient", lambda: DummyClient(captured))
    await rest_client.get_json("/api/foo", ctx=ctx)
    assert captured["headers"]["Authorization"] == "tg secret"


@pytest.mark.asyncio
async def test_timezone_webapp_init_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        onboarding.onboarding_state, "load_state", AsyncMock(return_value=None)
    )
    msg = DummyMessage(json.dumps({"timezone": "Bad/Zone", "init_data": "secret"}))
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=msg, effective_user=SimpleNamespace(id=1)
        ),
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    state = await onboarding.timezone_webapp(update, ctx)
    assert state == onboarding.TIMEZONE
    assert ctx.user_data["tg_init_data"] == "secret"
    await _assert_header(ctx, monkeypatch)


@pytest.mark.asyncio
async def test_profile_webapp_init_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        profile_conv, "get_api", lambda: (None, Exception, object)
    )
    msg = DummyMessage(json.dumps({"init_data": "secret"}))
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=msg, effective_user=SimpleNamespace(id=1)
        ),
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await profile_conv.profile_webapp_save(update, ctx)
    assert ctx.user_data["tg_init_data"] == "secret"
    await _assert_header(ctx, monkeypatch)


@pytest.mark.asyncio
async def test_reminder_webapp_init_data(monkeypatch: pytest.MonkeyPatch) -> None:
    msg = DummyMessage(json.dumps({"init_data": "secret"}))
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=msg, effective_user=SimpleNamespace(id=1)
        ),
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await reminder.reminder_webapp_save(update, ctx)
    assert ctx.user_data["tg_init_data"] == "secret"
    await _assert_header(ctx, monkeypatch)


@pytest.mark.asyncio
async def test_existing_init_data_authorizes_request(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    init_data = build_init_data()
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": init_data}),
    )
    class Settings:
        api_url = "http://example"
        internal_api_key: str | None = None

    monkeypatch.setattr(rest_client, "get_settings", lambda: Settings())
    captured: dict[str, object] = {}
    monkeypatch.setattr(httpx, "AsyncClient", lambda: DummyClient(captured))
    await rest_client.get_json("/api/foo", ctx=ctx)
    assert captured["headers"]["Authorization"] == f"tg {init_data}"

    monkeypatch.setattr(settings, "telegram_token", TOKEN)

    async def _noop(_uid: int) -> None:
        return None

    monkeypatch.setattr(profile_router, "get_learning_profile", _noop)
    app = FastAPI()
    app.include_router(profile_router.router)
    with TestClient(app) as client, caplog.at_level(logging.WARNING):
        resp = client.get(
            "/profile/self", headers={"Authorization": f"tg {init_data}"}
        )
    assert resp.status_code == 200
    assert "/profile/self called without tg_init_data" not in caplog.text

