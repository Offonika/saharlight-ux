from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import gpt_handlers
from services.api.app.diabetes.handlers import registration


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.replies.append(text)


def make_update(message: DummyMessage) -> Update:
    return cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )


def make_context(
    user_data: dict[str, Any] | None = None,
) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data=user_data if user_data is not None else {}, job_queue=None
        ),
    )


@pytest.mark.asyncio
async def test_start_gpt_sets_flag() -> None:
    message = DummyMessage("/gpt")
    update = make_update(message)
    context = make_context({})
    await registration.start_gpt_dialog(update, context)
    assert context.user_data.get(registration.GPT_MODE_KEY) is True


@pytest.mark.asyncio
async def test_cancel_clears_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("/cancel")
    update = make_update(message)
    user_data = {registration.GPT_MODE_KEY: True}
    fake_cancel = AsyncMock()
    monkeypatch.setattr(
        "services.api.app.diabetes.handlers.dose_calc.dose_cancel", fake_cancel
    )
    context = make_context(user_data)
    await registration.cancel(update, context)
    assert registration.GPT_MODE_KEY not in user_data
    fake_cancel.assert_awaited_once()


@pytest.mark.asyncio
async def test_freeform_routes_to_gpt(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("hello")
    update = make_update(message)
    context = make_context({registration.GPT_MODE_KEY: True})
    chat_called = AsyncMock()
    monkeypatch.setattr(gpt_handlers, "chat_with_gpt", chat_called)

    def fail_parse(*args: object, **kwargs: object) -> None:
        raise AssertionError("parse_quick_values should not be called")

    monkeypatch.setattr(gpt_handlers, "parse_quick_values", fail_parse)
    await gpt_handlers.freeform_handler(update, context)
    chat_called.assert_awaited_once()
