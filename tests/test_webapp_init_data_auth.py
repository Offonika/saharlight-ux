import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest
from telegram import Update
from telegram.ext import CallbackContext

import importlib

import services.api.rest_client as rest_client
import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.diabetes.handlers.reminder_handlers as reminder

profile_conv = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)


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


class DummyPersistence:
    def __init__(self) -> None:
        self.updated: list[tuple[int, dict[str, object]]] = []

    async def update_user_data(
        self, user_id: int, data: dict[str, object]
    ) -> None:
        self.updated.append((user_id, dict(data)))


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
    persistence = DummyPersistence()
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, application=SimpleNamespace(persistence=persistence)),
    )
    state = await onboarding.timezone_webapp(update, ctx)
    assert state == onboarding.TIMEZONE
    assert ctx.user_data["tg_init_data"] == "secret"
    await _assert_header(ctx, monkeypatch)
    assert persistence.updated == [(1, {"tg_init_data": "secret"})]


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
    persistence = DummyPersistence()
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, application=SimpleNamespace(persistence=persistence)),
    )
    await profile_conv.profile_webapp_save(update, ctx)
    assert ctx.user_data["tg_init_data"] == "secret"
    await _assert_header(ctx, monkeypatch)
    assert persistence.updated == [(1, {"tg_init_data": "secret"})]


@pytest.mark.asyncio
async def test_reminder_webapp_init_data(monkeypatch: pytest.MonkeyPatch) -> None:
    msg = DummyMessage(json.dumps({"init_data": "secret"}))
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=msg, effective_user=SimpleNamespace(id=1)
        ),
    )
    persistence = DummyPersistence()
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, application=SimpleNamespace(persistence=persistence)),
    )
    await reminder.reminder_webapp_save(update, ctx)
    assert ctx.user_data["tg_init_data"] == "secret"
    await _assert_header(ctx, monkeypatch)
    assert persistence.updated == [(1, {"tg_init_data": "secret"})]

