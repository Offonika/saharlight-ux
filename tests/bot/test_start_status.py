from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import aiohttp
from aiohttp.client_reqrep import RequestInfo
import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.bot_start_handlers as start_handlers
from services.api.app.diabetes.bot_start_handlers import build_start_handler
from services.api.app.diabetes.bot_status_handlers import build_status_handler


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyResponse:
    def __init__(
        self, data: dict[str, Any], status: int = 200, message: str = ""
    ) -> None:
        self.status = status
        self._data = data
        self._message = message
        self.url = ""

    async def __aenter__(self) -> DummyResponse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                cast(RequestInfo, SimpleNamespace(real_url=self.url)),
                (),
                status=self.status,
                message=self._message,
            )

    async def json(self) -> dict[str, Any]:
        return self._data


class DummySession:
    def __init__(self, resp: DummyResponse) -> None:
        self._resp = resp
        self.timeout: aiohttp.ClientTimeout | None = None

    async def __aenter__(self) -> DummySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        *,
        timeout: aiohttp.ClientTimeout | None = None,
    ) -> DummyResponse:
        self.timeout = timeout
        self._resp.url = url
        return self._resp


@pytest.mark.asyncio
async def test_start_renders_cta(monkeypatch: pytest.MonkeyPatch) -> None:
    start_handlers.choose_variant = lambda _uid: "A"  # type: ignore[assignment]
    handler = build_start_handler("https://ui.example")
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "t"}),
    )

    await handler.callback(update, context)
    assert message.replies == [
        "👋 Добро пожаловать! Быстрая настройка в приложении:"
    ]
    buttons = message.kwargs[0]["reply_markup"].inline_keyboard
    assert "flow=onboarding" in buttons[0][0].web_app.url


@pytest.mark.asyncio
async def test_status_routes_to_missing_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    resp = DummyResponse(
        {"completed": False, "missing": ["reminders"], "step": "reminders"}
    )
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: DummySession(resp))

    handler = build_status_handler(
        "https://ui.example", api_base="https://api.example"
    )
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handler.callback(update, context)
    buttons = message.kwargs[0]["reply_markup"].inline_keyboard
    assert buttons[0][0].web_app.url.endswith(
        "/reminders?flow=onboarding&step=reminders"
    )


@pytest.mark.asyncio
async def test_status_handles_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    resp = DummyResponse({}, status=500, message="boom")
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: DummySession(resp))

    handler = build_status_handler(
        "https://ui.example", api_base="https://api.example"
    )
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handler.callback(update, context)
    assert message.replies == ["Не удалось получить статус онбординга: boom"]
