"""Unit tests for helper functions in :mod:`gpt_handlers`."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from telegram import Message, Update
from telegram.ext import CallbackContext

import pytest

import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers
from services.api.app.diabetes.handlers import UserData


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # noqa: ANN401
        self.replies.append((text, kwargs))


def make_update(message: DummyMessage) -> Update:
    return cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )


def make_context(
    user_data: dict[str, Any] | None = None,
) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data if user_data is not None else {}),
    )


@pytest.mark.asyncio
async def test_handle_pending_entry_numeric() -> None:
    message = DummyMessage("1")
    update = make_update(message)
    entry: dict[str, Any] = {}
    user_data = cast(
        UserData, {"pending_entry": entry, "pending_fields": ["xe", "dose"]}
    )
    context = make_context(cast(dict[str, Any], user_data))
    handled = await gpt_handlers.handle_pending_entry(
        update, context, "1", user_data, cast(Message, message), 1
    )
    assert handled is True
    assert entry["xe"] == 1
    assert user_data["pending_fields"] == ["dose"]


@pytest.mark.asyncio
async def test_handle_edit_mode_value_error() -> None:
    message = DummyMessage("abc")
    update = make_update(message)
    user_data = cast(UserData, {"edit_id": 1, "edit_field": "sugar"})
    context = make_context(cast(dict[str, Any], user_data))
    handled = await gpt_handlers.handle_edit_mode(
        update, context, "abc", user_data, cast(Message, message)
    )
    assert handled is True
    assert "значение" in message.replies[0][0]


@pytest.mark.asyncio
async def test_handle_smart_input_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("?")
    update = make_update(message)
    user_data = cast(UserData, {})
    context = make_context(cast(dict[str, Any], user_data))

    def fake_smart_input(_: str) -> dict[str, float | None]:
        return {"sugar": None, "xe": None, "dose": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    handled = await gpt_handlers.handle_smart_input(
        update, context, "?", user_data, cast(Message, message), 1
    )
    assert handled is False


@pytest.mark.asyncio
async def test_handle_parsed_command_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("hello")
    update = make_update(message)
    user_data = cast(UserData, {})
    context = make_context(cast(dict[str, Any], user_data))

    async def fake_parse(_: str) -> dict[str, Any]:
        return {}

    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    handled = await gpt_handlers.handle_parsed_command(
        update, context, "hello", user_data, cast(Message, message), 1
    )
    assert handled is False
