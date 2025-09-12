import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram.ext import ApplicationHandlerStop

from services.api.app.diabetes.handlers import assistant_router
from services.api.app.diabetes import assistant_state, learning_handlers
from services.api.app.diabetes.handlers import gpt_handlers
from services.api.app.diabetes.utils.ui import SUGAR_BUTTON_TEXT
from services.api.app.diabetes.metrics import assistant_mode_total


@pytest.mark.asyncio
async def test_router_learn_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    async def fake(update, context):  # type: ignore[override]
        nonlocal called
        called = True

    monkeypatch.setattr(learning_handlers, "on_any_text", fake)
    update = MagicMock()
    message = MagicMock()
    message.text = "hi"
    update.message = message
    ctx = MagicMock()
    ctx.user_data = {"assistant_last_mode": "learn"}

    with pytest.raises(ApplicationHandlerStop):
        await assistant_router.on_any_text(update, ctx)

    assert called
    assert ctx.user_data.get(assistant_state.AWAITING_KIND) == "learn"


@pytest.mark.asyncio
async def test_router_chat_routes(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    called = False

    async def fake(update, context):  # type: ignore[override]
        nonlocal called
        called = True

    monkeypatch.setattr(gpt_handlers, "freeform_handler", fake)
    update = MagicMock()
    message = MagicMock()
    message.text = "hi"
    update.message = message
    update.effective_user = MagicMock(id=77)
    ctx = MagicMock()
    ctx.user_data = {"assistant_last_mode": "chat"}
    base = assistant_mode_total.labels(mode="chat")._value.get()
    with caplog.at_level(logging.INFO), pytest.raises(ApplicationHandlerStop):
        await assistant_router.on_any_text(update, ctx)

    assert called
    assert ctx.user_data.get(assistant_state.AWAITING_KIND) == "chat"
    assert assistant_mode_total.labels(mode="chat")._value.get() == base + 1
    record = next(r for r in caplog.records if r.message == "assistant_mode_request")
    assert record.mode == "chat"
    assert record.user_id == 77


@pytest.mark.asyncio
async def test_router_labs_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    update = MagicMock()
    message = MagicMock()
    message.text = "result"
    message.reply_text = AsyncMock()
    update.message = message
    ctx = MagicMock()
    ctx.user_data = {"assistant_last_mode": "labs"}

    with pytest.raises(ApplicationHandlerStop):
        await assistant_router.on_any_text(update, ctx)

    assert ctx.user_data.get("waiting_labs") is True
    message.reply_text.assert_awaited_once()
    assert ctx.user_data.get("assistant_last_mode") is None
    assert ctx.user_data.get(assistant_state.AWAITING_KIND) == "labs"


@pytest.mark.asyncio
async def test_router_visit_checklist() -> None:
    update = MagicMock()
    message = MagicMock()
    message.text = "visit"
    message.reply_text = AsyncMock()
    update.message = message
    ctx = MagicMock()
    ctx.user_data = {"assistant_last_mode": "visit"}

    with pytest.raises(ApplicationHandlerStop):
        await assistant_router.on_any_text(update, ctx)

    message.reply_text.assert_awaited_once()
    assert ctx.user_data.get("assistant_last_mode") is None
    assert ctx.user_data.get(assistant_state.AWAITING_KIND) == "visit"


@pytest.mark.asyncio
async def test_router_passes_menu_buttons(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    async def fake(update, context):  # type: ignore[override]
        nonlocal called
        called = True

    monkeypatch.setattr(gpt_handlers, "freeform_handler", fake)
    update = MagicMock()
    message = MagicMock()
    message.text = SUGAR_BUTTON_TEXT
    update.message = message
    ctx = MagicMock()
    ctx.user_data = {"assistant_last_mode": "chat"}

    await assistant_router.on_any_text(update, ctx)

    assert called is False
    assert ctx.user_data.get("assistant_last_mode") == "chat"
    assert assistant_state.AWAITING_KIND not in ctx.user_data
