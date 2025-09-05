from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import aiohttp
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
    def __init__(self, data: dict[str, Any]) -> None:
        self.status = 200
        self._data = data

    async def __aenter__(self) -> DummyResponse:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def json(self) -> dict[str, Any]:
        return self._data


class DummySession:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    async def __aenter__(self) -> DummySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, headers: dict[str, str] | None = None) -> DummyResponse:
        return DummyResponse(self._data)


@pytest.mark.asyncio
async def test_status_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    resp = {"completed": False, "missing": ["profile", "reminders"]}
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: DummySession(resp))

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
    resp = {"completed": True, "missing": []}
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: DummySession(resp))

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
    markup = message.kwargs[0]["reply_markup"]
    buttons = markup.inline_keyboard
    assert buttons[0][0].web_app.url == (
        "https://ui.example/profile?flow=onboarding&step=profile"
    )
    assert buttons[1][0].web_app.url == (
        "https://ui.example/reminders?flow=onboarding&step=reminders"
    )
