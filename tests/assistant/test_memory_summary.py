from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session, sessionmaker
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes import assistant_state
from services.api.app.diabetes.handlers import gpt_handlers
from services.api.app.services import assistant_memory


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_summary_saved_and_limited(
    monkeypatch: pytest.MonkeyPatch, in_memory_db: sessionmaker[Session]
) -> None:
    monkeypatch.setattr(assistant_state, "ASSISTANT_MAX_TURNS", 2)
    monkeypatch.setattr(assistant_state, "ASSISTANT_SUMMARY_TRIGGER", 3)

    def fake_summarize(parts: list[str]) -> str:
        return ";".join(parts)

    monkeypatch.setattr(assistant_state, "summarize", fake_summarize)
    monkeypatch.setattr(assistant_memory, "SessionLocal", in_memory_db)

    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    for i in range(3):
        msg = DummyMessage(str(i))
        update = cast(
            Update,
            SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1)),
        )
        await gpt_handlers.chat_with_gpt(update, context)

    history = cast(list[str], context.user_data["assistant_history"])
    assert len(history) == 2

    summary = await assistant_memory.get_summary(1)
    assert summary is not None
    assert "user: 0" in summary


@pytest.mark.asyncio
async def test_reset_clears_db(
    monkeypatch: pytest.MonkeyPatch, in_memory_db: sessionmaker[Session]
) -> None:
    monkeypatch.setattr(assistant_memory, "SessionLocal", in_memory_db)
    await assistant_memory.save_summary(1, "old")

    user_data: dict[str, Any] = {
        "assistant_history": ["turn"],
        "assistant_summary": "old",
    }
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )
    await gpt_handlers.reset_command(update, context)

    assert context.user_data == {}
    assert await assistant_memory.get_summary(1) is None
    assert message.texts == ["История диалога очищена."]
