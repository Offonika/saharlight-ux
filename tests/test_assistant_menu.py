import pytest
from unittest.mock import AsyncMock, MagicMock

from services.api.app.diabetes.handlers import assistant_menu


def test_assistant_keyboard_layout() -> None:
    keyboard = assistant_menu.assistant_keyboard()
    data = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert data == ["asst:profile", "asst:reminders", "asst:report"]


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
    assert "asst:profile" in back


@pytest.mark.asyncio
async def test_assistant_callback_mode_has_back_button() -> None:
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:profile"
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
