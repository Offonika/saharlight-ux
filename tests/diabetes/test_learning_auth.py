from typing import Any, cast
from types import SimpleNamespace

import httpx
import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.learning_handlers as learning_handlers
from services.api.app.assistant.repositories.logs import pending_logs
from services.api.app.config import Settings
from services.api.app.diabetes import learning_onboarding as onboarding_utils
from services.api.rest_client import AuthRequiredError


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(
        self, text: str, **_kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)


async def _fake_hydrate(_u: object, _c: object) -> bool:
    return True


@pytest.mark.asyncio
async def test_learn_command_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        learning_handlers,
        "settings",
        Settings(
            LEARNING_MODE_ENABLED="1", LEARNING_CONTENT_MODE="dynamic", _env_file=None
        ),
    )
    monkeypatch.setattr(learning_handlers, "_hydrate", _fake_hydrate)

    request = httpx.Request("GET", "http://example/profile")
    response = httpx.Response(401, request=request)

    async def _fail(_user_id: int, _ctx: object) -> dict[str, object]:
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(learning_handlers.profiles, "get_profile_for_user", _fail)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "bad"}, bot_data={}),
    )

    await learning_handlers.learn_command(update, context)
    assert message.replies == [learning_handlers.AUTH_REQUIRED_MESSAGE]
    pending_logs.clear()


@pytest.mark.asyncio
async def test_learn_command_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        learning_handlers,
        "settings",
        Settings(LEARNING_MODE_ENABLED="1", LEARNING_CONTENT_MODE="dynamic", _env_file=None),
    )
    monkeypatch.setattr(learning_handlers, "_hydrate", _fake_hydrate)

    async def _fail(_user_id: int, _ctx: object) -> dict[str, object]:
        raise AuthRequiredError()

    monkeypatch.setattr(learning_handlers.profiles, "get_profile_for_user", _fail)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    await learning_handlers.learn_command(update, context)
    assert message.replies == [learning_handlers.AUTH_REQUIRED_MESSAGE]
    pending_logs.clear()


@pytest.mark.asyncio
async def test_ensure_overrides_missing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fail(_user_id: int, _ctx: object) -> dict[str, object]:
        raise AuthRequiredError()

    monkeypatch.setattr(onboarding_utils.profiles, "get_profile_for_user", _fail)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1), callback_query=None),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    result = await onboarding_utils.ensure_overrides(update, context)
    assert result is False
    assert message.replies == [learning_handlers.AUTH_REQUIRED_MESSAGE]
