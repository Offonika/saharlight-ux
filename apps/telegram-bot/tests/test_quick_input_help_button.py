import pytest
from types import SimpleNamespace

import diabetes.common_handlers as handlers


class DummyMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies = []
        self.kwargs = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_quick_input_help_button():
    """Simulate the "🕹 Быстрый ввод" menu button and verify the hint."""

    message = DummyMessage("🕹 Быстрый ввод")
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    await handlers.smart_input_help(update, context)

    assert message.replies, "Expected at least one reply"
    reply = message.replies[0]
    assert "сахар=" in reply
    assert "xe=" in reply or "XE" in reply
    assert "dose=" in reply or "ед" in reply
