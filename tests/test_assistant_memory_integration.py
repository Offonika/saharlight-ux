from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes import commands
from services.api.app.diabetes.handlers import gpt_handlers
from services.api.app.assistant.services import memory_service


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_memory_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, bool] = {"called": False}

    async def fake_get_memory(user_id: int) -> Any:
        called["called"] = True
        return SimpleNamespace()

    cleared: dict[str, bool] = {"called": False}

    async def fake_clear_memory(user_id: int) -> None:
        assert user_id == 1
        cleared["called"] = True

    monkeypatch.setattr(memory_service, "get_memory", fake_get_memory)
    monkeypatch.setattr(commands, "_clear_memory", fake_clear_memory)

    message = DummyMessage("hi")
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await gpt_handlers.chat_with_gpt(update, context)
    assert not called["called"]
    assert "assistant_summary" not in context.user_data

    reset_update = cast(Update, SimpleNamespace(effective_message=DummyMessage(), effective_user=user))
    reset_context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=context.user_data),
    )
    await commands.reset_command(reset_update, reset_context)
    assert reset_context.user_data == {}
    assert cleared["called"]
