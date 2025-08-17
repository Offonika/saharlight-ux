from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.profile as conv


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_profile_command_help(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=["help"], chat_data={}),
    )
    monkeypatch.setattr(conv, "get_api", lambda: (None, Exception, object))
    result = await conv.profile_command(update, context)
    assert result == conv.END
    assert message.texts and "Формат команды" in message.texts[0]

