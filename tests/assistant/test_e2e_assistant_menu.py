from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.ext import Application, ApplicationHandlerStop, CallbackContext

from services.bot.main import build_persistence
from services.api.app.diabetes import assistant_state, labs_handlers, learning_handlers
from services.api.app.diabetes.handlers import assistant_menu, assistant_router, gpt_handlers
from services.api.app.assistant.services import memory_service
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_menu_chat_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:chat"
    query.message = message
    query.answer = AsyncMock()
    update = SimpleNamespace(callback_query=query)
    ctx = SimpleNamespace(user_data=user_data)

    await assistant_menu.assistant_callback(update, ctx)

    called = False

    async def fake_freeform(update: object, context: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(gpt_handlers, "freeform_handler", fake_freeform)

    msg = MagicMock()
    msg.text = "hi"
    update2 = SimpleNamespace(message=msg)

    with pytest.raises(ApplicationHandlerStop):
        await assistant_router.on_any_text(update2, ctx)

    assert called is True
    assert user_data.get(assistant_state.AWAITING_KIND) == "chat"
    assert user_data.get(assistant_state.LAST_MODE_KEY) == "chat"


@pytest.mark.asyncio
async def test_menu_learn_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:learn"
    query.message = message
    query.answer = AsyncMock()
    update = SimpleNamespace(callback_query=query)
    ctx = SimpleNamespace(user_data=user_data)

    await assistant_menu.assistant_callback(update, ctx)

    called = False

    async def fake_learn(update: object, context: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(learning_handlers, "on_any_text", fake_learn)

    msg = MagicMock()
    msg.text = "lesson"
    update2 = SimpleNamespace(message=msg)

    with pytest.raises(ApplicationHandlerStop):
        await assistant_router.on_any_text(update2, ctx)

    assert called is True
    assert user_data.get(assistant_state.AWAITING_KIND) == "learn"
    assert user_data.get(assistant_state.LAST_MODE_KEY) == "learn"


@pytest.mark.asyncio
async def test_menu_labs_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:labs"
    query.message = message
    query.answer = AsyncMock()
    update = SimpleNamespace(callback_query=query)
    ctx = SimpleNamespace(user_data=user_data, bot=MagicMock())

    await assistant_menu.assistant_callback(update, ctx)
    assert user_data.get("waiting_labs") is True

    msg1 = MagicMock()
    msg1.text = None
    msg1.document = None
    msg1.photo = None
    msg1.reply_text = AsyncMock()
    upd1 = SimpleNamespace(message=msg1, effective_message=msg1)
    await labs_handlers.labs_handler(upd1, ctx)
    msg1.reply_text.assert_awaited_once()
    assert "⚠️" in msg1.reply_text.call_args.args[0]
    assert user_data.get("waiting_labs") is None

    await assistant_menu.assistant_callback(update, ctx)
    monkeypatch.setattr(labs_handlers, "build_main_keyboard", lambda: None)

    msg2 = MagicMock()
    msg2.text = "глюкоза: 5"
    msg2.document = None
    msg2.photo = None
    msg2.reply_text = AsyncMock()
    upd2 = SimpleNamespace(message=msg2, effective_message=msg2)
    await labs_handlers.labs_handler(upd2, ctx)
    msg2.reply_text.assert_awaited_once()
    assert "глюкоза" in msg2.reply_text.call_args.args[0]
    assert user_data.get("waiting_labs") is None
    assert user_data.get(labs_handlers.AWAITING_KIND) == labs_handlers.KIND_TEXT


@pytest.mark.asyncio
async def test_menu_visit_save_note(monkeypatch: pytest.MonkeyPatch) -> None:
    user_data: dict[str, object] = {}

    async def fake_profile(user_id: int) -> Any:
        return SimpleNamespace(target_bg=None)

    async def fake_memory(user_id: int) -> None:
        return None

    monkeypatch.setattr(profile_service, "get_profile", fake_profile)
    monkeypatch.setattr(memory_service, "get_memory", fake_memory)
    monkeypatch.setattr(memory_service, "set_last_mode", AsyncMock())

    message = MagicMock()
    message.edit_text = AsyncMock()
    message.reply_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:visit"
    query.message = message
    query.answer = AsyncMock()
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1), effective_message=message)
    ctx = SimpleNamespace(user_data=user_data)

    await assistant_menu.assistant_callback(update, ctx)
    message.reply_text.assert_awaited_once()
    note = cast(str, user_data.get("visit_note"))
    assert "Чек-лист визита" in note

    async def fake_save_note(user_id: int, text: str) -> None:
        saved["text"] = text

    saved: dict[str, str] = {}
    monkeypatch.setattr(memory_service, "save_note", fake_save_note)
    save_query = MagicMock()
    save_query.data = "asst:save_note"
    save_query.answer = AsyncMock()
    save_query.edit_message_text = AsyncMock()
    save_update = SimpleNamespace(callback_query=save_query, effective_user=SimpleNamespace(id=1))

    await assistant_menu.assistant_callback(save_update, ctx)
    assert saved["text"] == note
    save_query.edit_message_text.assert_awaited_once()
    assert "visit_note" not in user_data


@pytest.mark.asyncio
async def test_last_mode_restored_after_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    persistence_path = tmp_path / "state.pkl"

    from telegram.ext import ExtBot

    async def dummy_initialize(self: ExtBot) -> None:
        return None

    async def dummy_shutdown(self: ExtBot) -> None:
        return None

    monkeypatch.setattr(ExtBot, "initialize", dummy_initialize)
    monkeypatch.setattr(ExtBot, "shutdown", dummy_shutdown)
    monkeypatch.setenv("BOT_PERSISTENCE_PATH", str(persistence_path))

    persistence1 = build_persistence()
    app1 = Application.builder().token("TOKEN").persistence(persistence1).build()
    await app1.initialize()

    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:chat"
    query.message = message
    query.answer = AsyncMock()
    update = SimpleNamespace(callback_query=query)
    ctx1: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]] = CallbackContext(app1, user_id=1)
    await assistant_menu.assistant_callback(update, ctx1)
    await app1.persistence.update_user_data(1, app1.user_data[1])
    await app1.persistence.flush()
    await app1.shutdown()

    persistence2 = build_persistence()
    app2 = Application.builder().token("TOKEN").persistence(persistence2).build()
    await app2.initialize()

    ctx2: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]] = CallbackContext(app2, user_id=1)
    assert ctx2.user_data.get(assistant_state.LAST_MODE_KEY) == "chat"

    called = False

    async def fake_freeform(update: object, context: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(gpt_handlers, "freeform_handler", fake_freeform)

    msg = MagicMock()
    msg.text = "hello"
    upd = SimpleNamespace(message=msg)
    with pytest.raises(ApplicationHandlerStop):
        await assistant_router.on_any_text(upd, ctx2)
    assert called is True
    await app2.shutdown()


@pytest.mark.asyncio
async def test_unknown_callback_data() -> None:
    user_data: dict[str, object] = {}
    message = MagicMock()
    message.edit_text = AsyncMock()
    query = MagicMock()
    query.data = "asst:unknown"
    query.message = message
    query.answer = AsyncMock()
    update = SimpleNamespace(callback_query=query)
    ctx = SimpleNamespace(user_data=user_data)
    await assistant_menu.assistant_callback(update, ctx)
    message.edit_text.assert_awaited_once()
    assert "Неизвестная команда" in message.edit_text.call_args.args[0]
    assert user_data.get(assistant_state.LAST_MODE_KEY) == "unknown"


@pytest.mark.asyncio
async def test_labs_handler_unsupported_file() -> None:
    user_data: dict[str, object] = {"waiting_labs": True}
    message = MagicMock()
    message.text = None
    message.document = None
    message.photo = None
    message.voice = SimpleNamespace(file_id="1")
    message.reply_text = AsyncMock()
    ctx = SimpleNamespace(user_data=user_data, bot=MagicMock())
    update = SimpleNamespace(message=message, effective_message=message)
    await labs_handlers.labs_handler(update, ctx)
    message.reply_text.assert_awaited_once()
    assert "⚠️" in message.reply_text.call_args.args[0]
    assert "waiting_labs" not in user_data
