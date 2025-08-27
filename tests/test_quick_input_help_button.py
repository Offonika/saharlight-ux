import pytest
from typing import Any

import services.api.app.diabetes.handlers.common_handlers as handlers
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_quick_input_help_button() -> None:
    """Simulate the "🕹 Быстрый ввод" menu button and verify the hint."""

    message = DummyMessage("🕹 Быстрый ввод")
    update = make_update(message=message)
    context = make_context()

    await handlers.smart_input_help(update, context)

    assert message.replies, "Expected at least one reply"
    reply = message.replies[0]
    assert "сахар=" in reply
    assert "xe=" in reply or "XE" in reply
    assert "dose=" in reply or "ед" in reply
