from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.diabetes import assistant_state
from services.api.app.diabetes import commands


@pytest.mark.asyncio
async def test_history_trim_and_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assistant_state, "ASSISTANT_MAX_TURNS", 2)
    monkeypatch.setattr(assistant_state, "ASSISTANT_SUMMARY_TRIGGER", 3)

    def fake_summary(parts: list[str]) -> str:
        return ",".join(parts)

    monkeypatch.setattr(assistant_state, "summarize", fake_summary)

    data: dict[str, Any] = {}
    assistant_state.add_turn(data, "a1")
    assistant_state.add_turn(data, "a2")
    assert data[assistant_state.HISTORY_KEY] == ["a1", "a2"]

    assistant_state.add_turn(data, "a3")
    assert data[assistant_state.HISTORY_KEY] == ["a2", "a3"]
    assert data[assistant_state.SUMMARY_KEY] == "a1"


@pytest.mark.asyncio
async def test_reset_command_clears(monkeypatch: pytest.MonkeyPatch) -> None:
    user_data: dict[str, Any] = {
        assistant_state.HISTORY_KEY: ["x"],
        assistant_state.SUMMARY_KEY: "y",
    }
    replies: list[str] = []

    class DummyMessage:
        async def reply_text(self, text: str, **_: Any) -> None:
            replies.append(text)

    update = SimpleNamespace(effective_message=DummyMessage())
    context = SimpleNamespace(user_data=user_data)
    await commands.reset_command(update, context)
    assert user_data == {}
    assert replies and "очищ" in replies[0].lower()


def test_reset_mode_state() -> None:
    data = {
        assistant_state.LAST_MODE_KEY: "chat",
        assistant_state.AWAITING_KIND: "chat",
    }
    assistant_state.reset_mode_state(data)
    assert data == {}


def test_get_last_mode_initializes_with_default() -> None:
    data: dict[str, Any] = {}
    mode = assistant_state.get_last_mode(data)
    assert mode == assistant_state.ASSISTANT_DEFAULT_MODE
    assert data[assistant_state.LAST_MODE_KEY] == assistant_state.ASSISTANT_DEFAULT_MODE


def test_default_mode_from_env() -> None:
    assert assistant_state.ASSISTANT_DEFAULT_MODE == "menu"
