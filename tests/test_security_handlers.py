import pytest
from typing import Any

import services.api.app.diabetes.handlers.security_handlers as handlers
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_hypoalert_faq_returns_message() -> None:
    message = DummyMessage()
    update = make_update(message=message)
    context = make_context()

    await handlers.hypo_alert_faq(update, context)

    assert message.replies, "Handler should reply with text"
    text = message.replies[0]
    assert "Гипогликемия" in text
    assert "Раннее предупреждение" in text
