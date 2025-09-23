from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fastapi import HTTPException

from services.api.app.diabetes import visit_handlers


@pytest.mark.asyncio
async def test_send_checklist(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = MagicMock()
    profile.target_bg = 5.5
    monkeypatch.setattr(
        visit_handlers.profile_service, "get_profile", AsyncMock(return_value=profile)
    )
    monkeypatch.setattr(
        visit_handlers.memory_service, "get_memory", AsyncMock(return_value=None)
    )
    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock()
    update.effective_user.id = 1
    update.effective_message = message
    ctx = MagicMock()
    ctx.user_data = {}

    await visit_handlers.send_checklist(update, ctx)

    message.reply_text.assert_awaited_once()
    markup = message.reply_text.call_args.kwargs["reply_markup"]
    data = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert "asst:save_note" in data
    assert "visit_note" in ctx.user_data


@pytest.mark.asyncio
async def test_save_note_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(visit_handlers.memory_service, "save_note", AsyncMock())
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    update.effective_user.id = 2
    ctx = MagicMock()
    ctx.user_data = {"visit_note": "note"}

    await visit_handlers.save_note_callback(update, ctx)

    visit_handlers.memory_service.save_note.assert_awaited_once_with(2, "note")
    query.edit_message_text.assert_awaited_once()
    assert ctx.user_data == {}


@pytest.mark.asyncio
async def test_send_checklist_profile_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        visit_handlers.profile_service,
        "get_profile",
        AsyncMock(side_effect=HTTPException(status_code=404, detail="not found")),
    )
    memory_mock = AsyncMock()
    monkeypatch.setattr(visit_handlers.memory_service, "get_memory", memory_mock)
    message = MagicMock()
    message.reply_text = AsyncMock()
    update = MagicMock()
    update.effective_user.id = 3
    update.effective_message = message
    ctx = MagicMock()
    ctx.user_data = {}

    await visit_handlers.send_checklist(update, ctx)

    message.reply_text.assert_awaited_once_with(
        "Заполните, пожалуйста, профиль, чтобы мы могли подготовить чек-лист."
    )
    memory_mock.assert_not_awaited()
    assert "visit_note" not in ctx.user_data
