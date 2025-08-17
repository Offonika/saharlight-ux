import logging
import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.data = data
        self.message = message
        self.edited: list[str] = []
        self.edit_kwargs: list[dict[str, Any]] = []

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)
        self.edit_kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_callback_router_cancel_entry_sends_menu() -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router
    from services.api.app.diabetes.handlers import common_handlers

    query = DummyQuery(DummyMessage(), "cancel_entry")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {"telegram_id": 1}}),
    )

    await router.callback_router(update, context)

    assert query.edited == ["❌ Запись отменена."]
    assert query.edit_kwargs
    kwargs0 = query.edit_kwargs[0]
    assert not kwargs0 or "reply_markup" not in kwargs0
    assert len(query.message.replies) == 1
    assert query.message.kwargs
    kwargs = query.message.kwargs[0]
    assert kwargs.get("reply_markup") == common_handlers.menu_keyboard
    assert context.user_data is not None
    user_data = context.user_data
    assert "pending_entry" not in user_data


@pytest.mark.asyncio
async def test_callback_router_invalid_entry_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery(DummyMessage(), "del:abc")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    with caplog.at_level(logging.WARNING):
        await router.callback_router(update, context)

    assert query.edited == ["Некорректный идентификатор записи."]
    assert "Invalid entry_id in callback data" in caplog.text


@pytest.mark.asyncio
async def test_callback_router_unknown_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery(DummyMessage(), "foo")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    with caplog.at_level(logging.WARNING):
        await router.callback_router(update, context)

    assert query.edited == ["Команда не распознана"]
    assert "Unrecognized callback data" in caplog.text


@pytest.mark.asyncio
async def test_callback_router_ignores_reminder_action() -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery(DummyMessage(), "rem_toggle:1")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}}),
    )

    await router.callback_router(update, context)

    assert query.edited == []
    assert context.user_data is not None
    user_data = context.user_data
    assert "pending_entry" in user_data
