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
        self.markups: list[object | None] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))


@pytest.mark.asyncio
async def test_trial_command_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://api.test/api")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://example.org")
    config.reload_settings()

    end_date = "2025-01-15T00:00:00+00:00"

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def post(self, url: str, params: dict[str, int], timeout: float) -> httpx.Response:
            assert url == "http://api.test/api/billing/trial"
            assert params == {"user_id": 42}
            req = httpx.Request("POST", url)
            return httpx.Response(200, request=req, json={"endDate": end_date})

    monkeypatch.setattr(billing_handlers.httpx, "AsyncClient", lambda: DummyClient())

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=42),
            callback_query=None,
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.trial_command(update, context)

    assert message.texts == [
        "🎉 Активирован trial до 15.01.2025",
        (
            "🟢 Подписка PRO даёт расширенные функции:\n"
            "• Распознавание блюд по фото\n"
            "• Чат с GPT\n"
            "• Расширенные напоминания\n\n"
            "👉 Чтобы оформить подписку, нажмите кнопку ниже:"
        ),
    ]
    markup = message.markups[1]
    button = markup.inline_keyboard[0][0]
    assert button.text == "💳 Оформить PRO"
    assert button.web_app and button.web_app.url == config.build_ui_url("/subscription")
    monkeypatch.delenv("API_URL")
    monkeypatch.delenv("PUBLIC_ORIGIN")
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
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=1),
            callback_query=None,
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.trial_command(update, context)

    assert message.texts == ["❌ Не удалось активировать trial. Попробуйте позже."]
    monkeypatch.delenv("API_URL")
    config.reload_settings()


@pytest.mark.asyncio
async def test_trial_command_already_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://api.test/api")
    config.reload_settings()

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def post(self, url: str, params: dict[str, int], timeout: float) -> httpx.Response:
            req = httpx.Request("POST", url)
            return httpx.Response(409, request=req, json={"detail": "Trial already active"})

        async def get(self, url: str, params: dict[str, int], timeout: float) -> httpx.Response:
            req = httpx.Request("GET", url)
            return httpx.Response(
                200,
                request=req,
                json={"subscription": {"endDate": "2025-01-16T00:00:00+00:00"}},
            )

    monkeypatch.setattr(billing_handlers.httpx, "AsyncClient", lambda: DummyClient())

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message, effective_user=SimpleNamespace(id=42), callback_query=None
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.trial_command(update, context)

    assert message.texts == ["🎁 Пробный период уже активен до 16.01.2025"]
    monkeypatch.delenv("API_URL")
    config.reload_settings()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{}, {"endDate": "oops"}, {"endDate": 123}])
async def test_trial_command_bad_end_date(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> None:
    monkeypatch.setenv("API_URL", "http://api.test/api")
    config.reload_settings()

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def post(self, url: str, params: dict[str, int], timeout: float) -> httpx.Response:
            req = httpx.Request("POST", url)
            return httpx.Response(200, request=req, json=payload)

    monkeypatch.setattr(billing_handlers.httpx, "AsyncClient", lambda: DummyClient())

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=1),
            callback_query=None,
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.trial_command(update, context)

    assert message.texts == ["❌ Ошибка сервера: неверный формат даты trial."]
    monkeypatch.delenv("API_URL")
    config.reload_settings()


@pytest.mark.asyncio
async def test_upgrade_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://example.org")
    config.reload_settings()

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1), callback_query=None),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await billing_handlers.upgrade_command(update, context)

    assert message.texts == [
        (
            "🟢 Подписка PRO даёт расширенные функции:\n"
            "• Распознавание блюд по фото\n"
            "• Чат с GPT\n"
            "• Расширенные напоминания\n\n"
            "👉 Чтобы оформить подписку, нажмите кнопку ниже:"
        )
    ]
    markup = message.markups[0]
    button = markup.inline_keyboard[0][0]
    assert button.text == "💳 Оформить PRO"
    assert button.web_app and button.web_app.url == config.build_ui_url("/subscription")
    monkeypatch.delenv("PUBLIC_ORIGIN")
    config.reload_settings()


@pytest.mark.asyncio
async def test_subscription_status_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://api.test/api")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://example.org")
    config.reload_settings()

    statuses = [
        {
            "featureFlags": {
                "billingEnabled": True,
                "paywallMode": "soft",
                "testMode": False,
            },
            "subscription": None,
        },
        {
            "featureFlags": {
                "billingEnabled": True,
                "paywallMode": "soft",
                "testMode": False,
            },
            "subscription": {
                "plan": "pro",
                "status": "TRIAL",
                "provider": "dummy",
                "startDate": "2025-01-01T00:00:00+00:00",
                "endDate": "2025-01-14T00:00:00+00:00",
            },
        },
        {
            "featureFlags": {
                "billingEnabled": True,
                "paywallMode": "soft",
                "testMode": False,
            },
            "subscription": {
                "plan": "pro",
                "status": "active",
                "provider": "dummy",
                "startDate": "2025-01-15T00:00:00+00:00",
                "endDate": "2025-02-14T00:00:00+00:00",
            },
        },
        {
            "featureFlags": {
                "billingEnabled": True,
                "paywallMode": "soft",
                "testMode": False,
            },
            "subscription": {
                "plan": "pro",
                "status": "expired",
                "provider": "dummy",
                "startDate": "2025-02-15T00:00:00+00:00",
                "endDate": "2025-03-15T00:00:00+00:00",
            },
        },
    ]

    idx = 0

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def get(self, url: str, params: dict[str, int], timeout: float) -> httpx.Response:
            nonlocal idx
            data = statuses[idx]
            idx += 1
            req = httpx.Request("GET", url)
            return httpx.Response(200, request=req, json=data)

    monkeypatch.setattr(billing_handlers.httpx, "AsyncClient", lambda: DummyClient())

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=1),
            callback_query=None,
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    for _ in range(4):
        await billing_handlers.subscription_button(update, context)

    assert message.texts == [
        "У вас нет подписки. Доступен 14-дневный trial",
        "Пробный период до 14.01.2025",
        "Подписка PRO до 14.02.2025",
        "Подписка истекла, оформите заново",
    ]
    # First markup has trial and upgrade buttons with proper labels
    first_row = message.markups[0].inline_keyboard[0]
    assert len(first_row) == 2
    trial_btn, upgrade_btn = first_row
    assert trial_btn.text == "🎁 Trial" and trial_btn.callback_data == "trial"
    assert upgrade_btn.text == "💳 Оформить PRO"
    assert upgrade_btn.web_app and upgrade_btn.web_app.url == config.build_ui_url("/subscription")
    # Subsequent keyboards only offer upgrade
    for kb in message.markups[1:]:
        assert len(kb.inline_keyboard[0]) == 1

    monkeypatch.delenv("API_URL")
    monkeypatch.delenv("PUBLIC_ORIGIN")
    config.reload_settings()
