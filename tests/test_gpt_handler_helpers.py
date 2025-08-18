from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers
from services.api.app.diabetes.handlers import UserData


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


def make_update(message: DummyMessage) -> Update:
    return cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )


def make_context(user_data: dict[str, Any]) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data, bot=SimpleNamespace()),
    )


@pytest.mark.asyncio
async def test_handle_pending_entry_invalid() -> None:
    message = DummyMessage("abc")
    update = make_update(message)
    user_data = {"pending_entry": {}, "pending_fields": ["xe"]}
    context = make_context(user_data)
    handled = await gpt_handlers.handle_pending_entry(
        update,
        context,
        cast(UserData, user_data),
        "abc",
        1,
    )
    assert handled is True
    assert message.replies == ["Введите число ХЕ."]


@pytest.mark.asyncio
async def test_handle_edit_mode_negative() -> None:
    message = DummyMessage("-1")
    update = make_update(message)
    user_data = {"edit_id": 1, "edit_field": "xe"}
    context = make_context(user_data)
    handled = await gpt_handlers.handle_edit_mode(
        update,
        context,
        cast(UserData, user_data),
        "-1",
    )
    assert handled is True
    assert message.replies == ["Значение не может быть отрицательным."]


@pytest.mark.asyncio
async def test_handle_smart_input_error(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("bad")
    update = make_update(message)
    user_data: dict[str, Any] = {}
    context = make_context(user_data)

    def fake_smart_input(text: str) -> dict[str, float | None]:
        raise ValueError("mismatched unit for xe")

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    handled = await gpt_handlers.handle_smart_input(
        update,
        context,
        cast(UserData, user_data),
        "bad",
        1,
    )
    assert handled is True
    assert message.replies[0].startswith("❗ ХЕ")


@pytest.mark.asyncio
async def test_handle_parsed_command_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("cmd")
    update = make_update(message)
    user_data: dict[str, Any] = {}
    context = make_context(user_data)

    async def fake_parse(text: str) -> dict[str, str]:
        return {"action": "noop"}

    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    handled = await gpt_handlers.handle_parsed_command(
        update,
        context,
        cast(UserData, user_data),
        "cmd",
        1,
    )
    assert handled is True
    assert message.replies == ["Не понял, воспользуйтесь /help или кнопками меню"]
