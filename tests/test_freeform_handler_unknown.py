import pytest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.dose_calc as handlers


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_freeform_handler_unknown_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("blah")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={})
    )

    monkeypatch.setattr(handlers, "parse_command", AsyncMock(return_value=None))

    await handlers.freeform_handler(update, context)

    assert message.replies
    assert (
        message.replies[0] == "Не понял, воспользуйтесь /help или кнопками меню"
    )