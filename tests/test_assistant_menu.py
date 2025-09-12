import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api.app.diabetes.handlers import assistant_menu
from services.api.app.diabetes import assistant_state, visit_handlers


def test_assistant_keyboard_layout() -> None:
    keyboard = assistant_menu.assistant_keyboard()
    data = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert data == ["asst:learn", "asst:chat", "asst:labs", "asst:visit"]


@pytest.mark.asyncio
async def test_assistant_callback_back_to_menu() -> None:
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:back"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query

    await assistant_menu.assistant_callback(update, MagicMock())

    query.answer.assert_awaited_once()
    message.edit_text.assert_awaited_once()
    markup = message.edit_text.call_args.kwargs["reply_markup"]
    back = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert "asst:learn" in back


@pytest.mark.asyncio
async def test_assistant_callback_mode_has_back_button() -> None:
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:chat"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query

    await assistant_menu.assistant_callback(update, MagicMock())

    query.answer.assert_awaited_once()
    message.edit_text.assert_awaited_once()
    markup = message.edit_text.call_args.kwargs["reply_markup"]
    callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert "asst:back" in callbacks


@pytest.mark.asyncio
async def test_assistant_callback_logs_selection(
    caplog: pytest.LogCaptureFixture,
) -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:chat"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    update.effective_user = MagicMock(id=42)
    ctx = MagicMock()
    ctx.user_data = user_data
    with caplog.at_level(logging.INFO):
        await assistant_menu.assistant_callback(update, ctx)
    record = next(r for r in caplog.records if r.message == "assistant_mode_selected")
    assert record.mode == "chat"
    assert record.user_id == 42


@pytest.mark.asyncio
async def test_assistant_callback_saves_mode() -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:learn"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.user_data = user_data

    await assistant_menu.assistant_callback(update, ctx)

    assert user_data.get("assistant_last_mode") == "learn"
    assert user_data.get(assistant_state.AWAITING_KIND) == "learn"


@pytest.mark.asyncio
async def test_assistant_callback_labs_waiting() -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:labs"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.user_data = user_data

    await assistant_menu.assistant_callback(update, ctx)

    assert user_data.get("waiting_labs") is True
    assert user_data.get("assistant_last_mode") is None
    assert user_data.get(assistant_state.AWAITING_KIND) == "labs"


@pytest.mark.asyncio
async def test_assistant_callback_visit_calls_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = AsyncMock()
    monkeypatch.setattr(visit_handlers, "send_checklist", handler)
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:visit"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    ctx = MagicMock()
    ctx.user_data = {}

    await assistant_menu.assistant_callback(update, ctx)

    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_assistant_callback_save_note_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = AsyncMock()
    monkeypatch.setattr(visit_handlers, "save_note_callback", handler)
    query = MagicMock()
    query.data = "asst:save_note"
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query

    await assistant_menu.assistant_callback(update, MagicMock())

    handler.assert_awaited_once()
