import logging
import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.edited: list[str] = []
        self.edit_kwargs: list[dict[str, Any]] = []
        self.message = DummyMessage()

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)
        self.edit_kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_handle_cancel_entry_sends_menu() -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router
    from services.api.app.diabetes.handlers import common_handlers

    query = DummyQuery("cancel_entry")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, Any, Any, Any],
        SimpleNamespace(user_data={"pending_entry": {"telegram_id": 1}}),
    )

    await router.handle_cancel_entry(update, context)

    assert query.edited == ["❌ Запись отменена."]
    assert not query.edit_kwargs[0] or "reply_markup" not in query.edit_kwargs[0]
    assert len(query.message.replies) == 1
    text, kwargs = query.message.replies[0]
    assert kwargs["reply_markup"] == common_handlers.menu_keyboard
    assert "pending_entry" not in context.user_data


@pytest.mark.asyncio
async def test_handle_delete_entry_invalid_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery("del:abc")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, Any, Any, Any],
        SimpleNamespace(user_data={}),
    )

    with caplog.at_level(logging.WARNING):
        await router.handle_delete_entry(update, context)

    assert query.edited == ["Некорректный идентификатор записи."]
    assert "Invalid entry_id in callback data" in caplog.text


@pytest.mark.asyncio
async def test_handle_unknown_callback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery("foo")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, Any, Any, Any],
        SimpleNamespace(user_data={}),
    )

    with caplog.at_level(logging.WARNING):
        await router.handle_unknown_callback(update, context)

    assert query.edited == ["Команда не распознана"]
    assert "Unrecognized callback data" in caplog.text


@pytest.mark.asyncio
async def test_handle_unknown_callback_ignores_reminder() -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery("rem_toggle:1")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, Any, Any, Any],
        SimpleNamespace(user_data={"pending_entry": {}}),
    )

    await router.handle_unknown_callback(update, context)

    assert query.edited == []
    assert "pending_entry" in context.user_data


@pytest.mark.asyncio
async def test_handle_edit_pending_entry() -> None:
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery("edit_entry")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, Any, Any, Any],
        SimpleNamespace(user_data={"pending_entry": {"telegram_id": 1}}),
    )

    await router.handle_edit_pending_entry(update, context)

    assert query.edited
    assert context.user_data.get("edit_id") is None
