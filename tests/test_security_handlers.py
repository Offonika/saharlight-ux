import pytest
from types import SimpleNamespace
from typing import Any

import services.api.app.diabetes.handlers.security_handlers as handlers


class DummyMessage:
    def __init__(self):
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_hypoalert_faq_returns_message() -> None:
    message = DummyMessage()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    await handlers.hypo_alert_faq(update, context)

    assert message.replies, "Handler should reply with text"
    text = message.replies[0]
    assert "Гипогликемия" in text
    assert "Раннее предупреждение" in text