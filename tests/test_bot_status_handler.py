from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import aiohttp
from aiohttp.client_reqrep import RequestInfo
import asyncio
import logging
import pytest
from telegram import Update
from telegram.ext import CallbackContext

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
async def test_status_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    resp = DummyResponse(
        {"completed": False, "missing": ["profile", "reminders"], "step": "profile"}
    )
    session = DummySession(resp)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: session)

    handler = build_status_handler("https://ui.example", api_base="https://api.example")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handler.callback(update, context)

    assert message.replies == ["Ещё пара шагов — продолжим настройку:"]
    assert isinstance(session.timeout, aiohttp.ClientTimeout)
    markup = message.kwargs[0]["reply_markup"]
    buttons = markup.inline_keyboard
    assert buttons[0][0].web_app.url == (
        "https://ui.example/profile?flow=onboarding&step=profile"
    )
    assert buttons[1][0].web_app.url == (
        "https://ui.example/reminders?flow=onboarding&step=reminders"
    )


@pytest.mark.asyncio
async def test_status_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    resp = DummyResponse({"completed": True, "missing": [], "step": None})
    session = DummySession(resp)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: session)

    handler = build_status_handler("https://ui.example", api_base="https://api.example")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handler.callback(update, context)

    assert message.replies == ["✅ Онбординг завершён. Чем помочь дальше?"]
    assert isinstance(session.timeout, aiohttp.ClientTimeout)
    markup = message.kwargs[0]["reply_markup"]
    buttons = markup.inline_keyboard
    assert buttons[0][0].web_app.url == (
        "https://ui.example/profile?flow=onboarding&step=profile"
    )
    assert buttons[1][0].web_app.url == (
        "https://ui.example/reminders?flow=onboarding&step=reminders"
    )


class ErrorSession:
    async def __aenter__(self) -> ErrorSession:
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
        raise aiohttp.ClientError


class TimeoutSession:
    async def __aenter__(self) -> TimeoutSession:
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
        raise asyncio.TimeoutError


@pytest.mark.asyncio
async def test_status_client_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: ErrorSession())

    handler = build_status_handler("https://ui.example", api_base="https://api.example")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    with caplog.at_level(logging.ERROR):
        await handler.callback(update, context)

    assert message.replies == ["Не удалось получить статус онбординга"]
    assert any("Status request failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_status_timeout_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: TimeoutSession())

    handler = build_status_handler("https://ui.example", api_base="https://api.example")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    with caplog.at_level(logging.ERROR):
        await handler.callback(update, context)

    assert message.replies == ["Не удалось получить статус онбординга"]
    assert any("Status request timed out" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_status_invalid_payload(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    session = DummySession(DummyResponse({"completed": "yes"}))
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: session)

    handler = build_status_handler("https://ui.example", api_base="https://api.example")
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    with caplog.at_level(logging.ERROR):
        await handler.callback(update, context)

    assert message.replies == ["Не удалось получить статус онбординга"]
    assert any("Invalid status response" in r.message for r in caplog.records)
