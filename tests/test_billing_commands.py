from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app import config
from services.api.app.diabetes.handlers import billing_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_trial_command_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://api.test/api")
    config.reload_settings()

    end_date = "2025-01-15T00:00:00+00:00"

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def post(
            self, url: str, params: dict[str, int], timeout: float
        ) -> httpx.Response:
            assert url == "http://api.test/api/billing/trial"
            assert params == {"user_id": 42}
            req = httpx.Request("POST", url)
            return httpx.Response(200, request=req, json={"endDate": end_date})

    monkeypatch.setattr(billing_handlers.httpx, "AsyncClient", lambda: DummyClient())

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=42)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.trial_command(update, context)

    assert message.texts == ["🎉 Пробный период активирован до 15.01.2025"]
    monkeypatch.delenv("API_URL")
    config.reload_settings()


@pytest.mark.asyncio
async def test_trial_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://api.test/api")
    config.reload_settings()

    class FailingClient:
        async def __aenter__(self) -> "FailingClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def post(self, url: str, params: dict[str, int], timeout: float) -> httpx.Response:
            raise httpx.HTTPError("boom")

    monkeypatch.setattr(billing_handlers.httpx, "AsyncClient", lambda: FailingClient())

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.trial_command(update, context)

    assert message.texts == [
        "❌ Не удалось активировать пробный период. Попробуйте позже."
    ]
    monkeypatch.delenv("API_URL")
    config.reload_settings()


@pytest.mark.asyncio
async def test_upgrade_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://example.org")
    config.reload_settings()

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.upgrade_command(update, context)

    assert message.texts == ["💳 Оформить подписку: http://example.org/ui/subscription"]
    monkeypatch.delenv("PUBLIC_ORIGIN")
    config.reload_settings()
