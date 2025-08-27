import pytest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.dose_handlers as dose_handlers
from services.api.app.diabetes.handlers.dose_handlers import freeform_handler


class DummyMessage:
    def __init__(self, text: str):
        self.text = text
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


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
        CallbackContext[Any, Any, Any, Any], SimpleNamespace(user_data={})
    )

    monkeypatch.setattr(dose_handlers, "parse_command", AsyncMock(return_value=None))

    await freeform_handler(update, context)

    assert message.replies
    assert message.replies[0][0] == "Не понял, воспользуйтесь /help или кнопками меню"
