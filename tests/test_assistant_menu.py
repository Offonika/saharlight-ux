import logging
from types import SimpleNamespace
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
async def test_assistant_callback_persists_mode(
    monkeypatch: pytest.MonkeyPatch,
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
    update.effective_user = MagicMock(id=7)
    ctx = MagicMock()
    ctx.user_data = user_data

    calls: list[tuple[int, str | None]] = []

    async def fake_set_last_mode(uid: int, mode: str | None) -> None:
        calls.append((uid, mode))

    monkeypatch.setattr(assistant_menu.memory_service, "set_last_mode", fake_set_last_mode)

    await assistant_menu.assistant_callback(update, ctx)

    assert calls == [(7, "chat")]


@pytest.mark.asyncio
async def test_assistant_callback_labs_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:labs"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    update.effective_user = MagicMock(id=8)
    ctx = MagicMock()
    ctx.user_data = user_data

    calls: list[tuple[int, str | None]] = []

    async def fake_set_last_mode(uid: int, mode: str | None) -> None:
        calls.append((uid, mode))

    monkeypatch.setattr(assistant_menu.memory_service, "set_last_mode", fake_set_last_mode)

    await assistant_menu.assistant_callback(update, ctx)

    assert user_data.get("waiting_labs") is True
    assert user_data.get("assistant_last_mode") is None
    assert user_data.get(assistant_state.AWAITING_KIND) == "labs"
    assert calls == [(8, None)]


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


@pytest.mark.asyncio
async def test_assistant_callback_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:unknown"
    query.message = message
    query.answer = AsyncMock()
    update = MagicMock()
    update.callback_query = query
    update.effective_user = MagicMock(id=13)
    ctx = MagicMock()
    ctx.user_data = {}
    with caplog.at_level(logging.WARNING):
        await assistant_menu.assistant_callback(update, ctx)
    message.edit_text.assert_awaited_once()
    assert ctx.user_data == {}
    record = next(r for r in caplog.records if r.message == "assistant_unknown_callback")
    assert record.data == "asst:unknown"


@pytest.mark.asyncio
async def test_post_init_restores_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_last_modes() -> list[tuple[int, str]]:
        return [(1, "chat"), (2, "learn")]

    monkeypatch.setattr(
        assistant_menu.memory_service, "get_last_modes", fake_get_last_modes
    )
    bot = MagicMock()
    bot.send_message = AsyncMock()
    app = SimpleNamespace(bot=bot, user_data={})

    await assistant_menu.post_init(app)

    assert app.user_data[1][assistant_state.LAST_MODE_KEY] == "chat"
    assert app.user_data[2][assistant_state.LAST_MODE_KEY] == "learn"
    assert bot.send_message.await_count == 2


def test_assistant_menu_emoji_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSISTANT_MENU_EMOJI", "false")
    from importlib import reload

    from services.api.app import config

    reload(config)
    config.reload_settings()
    import services.api.app.assistant.assistant_menu as helper
    import services.api.app.ui.keyboard as ui_keyboard
    import services.api.app.diabetes.handlers.assistant_menu as handler_menu

    reload(helper)
    reload(ui_keyboard)
    reload(handler_menu)

    assert helper.render_assistant_menu(False).assistant == "Ассистент_AI"
    assert ui_keyboard.LEARN_BUTTON_TEXT == "Ассистент_AI"
    texts = [
        btn.text for row in handler_menu.assistant_keyboard().inline_keyboard for btn in row
    ]
    assert texts == ["Обучение", "Чат", "Анализы", "Визит"]

    monkeypatch.delenv("ASSISTANT_MENU_EMOJI", raising=False)
    reload(config)
    config.reload_settings()
    reload(helper)
    reload(ui_keyboard)
    reload(handler_menu)
