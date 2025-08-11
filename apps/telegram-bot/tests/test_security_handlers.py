import pytest
from types import SimpleNamespace

import diabetes.security_handlers as handlers


class DummyMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text):
        self.replies.append(text)


@pytest.mark.asyncio
async def test_hypoalert_faq_returns_message():
    message = DummyMessage()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    await handlers.hypo_alert_faq(update, context)

    assert message.replies, "Handler should reply with text"
    text = message.replies[0]
    assert "Гипогликемия" in text
    assert "Раннее предупреждение" in text
