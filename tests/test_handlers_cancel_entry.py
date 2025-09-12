import datetime
import logging
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Chat, Message, Update
from telegram.ext import CallbackContext, ContextTypes
import services.api.app.ui.keyboard as kb


class DummyMessage(Message):
    __slots__ = ("replies", "kwargs")

    def __init__(self) -> None:
        super().__init__(
            message_id=1,
            date=datetime.datetime.now(),
            chat=Chat(id=1, type="private"),
        )
        object.__setattr__(self, "replies", [])
        object.__setattr__(self, "kwargs", [])

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
async def test_callback_router_cancel_entry_sends_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.handlers.router as router

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
    markup = kwargs.get("reply_markup")
    assert markup and markup.keyboard == kb.build_main_keyboard().keyboard
    assert context.user_data is not None
    user_data = context.user_data
    assert "pending_entry" not in user_data


@pytest.mark.asyncio
async def test_callback_router_invalid_entry_id(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")
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
async def test_handle_edit_or_delete_missing_colon(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.handlers.router as router

    query = DummyQuery(DummyMessage(), "del")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    with caplog.at_level(logging.WARNING):
        await router.handle_edit_or_delete(update, context, query, "del")

    assert query.edited == ["Некорректный формат данных."]
    assert "Invalid callback data format" in caplog.text


@pytest.mark.asyncio
async def test_callback_router_unknown_data(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")
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
async def test_callback_router_delegates_reminder_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
    import services.api.app.diabetes.handlers.router as router

    called: list[tuple[Update, ContextTypes.DEFAULT_TYPE]] = []

    async def fake_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        called.append((update, context))

    monkeypatch.setattr(reminder_handlers, "callback_router", fake_router, raising=False)

    query = DummyQuery(DummyMessage(), "rem_toggle:1")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}}),
    )

    await router.callback_router(update, context)

    assert called == [(update, context)]
    assert query.edited == []
    assert context.user_data is not None
    user_data = context.user_data
    assert "pending_entry" in user_data
