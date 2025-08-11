import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
import diabetes.dose_handlers as handlers


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


@pytest.mark.asyncio
async def test_freeform_handler_unknown_command(monkeypatch):
    message = DummyMessage("blah")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    monkeypatch.setattr(handlers, "parse_command", AsyncMock(return_value=None))

    await handlers.freeform_handler(update, context)

    assert message.replies
    assert message.replies[0][0] == "Не понял, воспользуйтесь /help или кнопками меню"
