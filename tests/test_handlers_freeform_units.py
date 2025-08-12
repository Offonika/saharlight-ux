import pytest
from types import SimpleNamespace
import services.api.app.diabetes.handlers.dose_handlers as handlers


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


@pytest.mark.asyncio
async def test_freeform_handler_warns_on_sugar_unit_mix():
    message = DummyMessage("сахар 5 XE")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    await handlers.freeform_handler(update, context)

    assert message.replies
    text, _ = message.replies[0]
    assert "ммоль/л" in text and "Сахар" in text


@pytest.mark.asyncio
async def test_freeform_handler_warns_on_dose_unit_mix():
    message = DummyMessage("доза 7 ммоль")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    await handlers.freeform_handler(update, context)

    assert message.replies
    text, _ = message.replies[0]
    assert "ед" in text.lower() and "доза" in text.lower()


@pytest.mark.asyncio
async def test_freeform_handler_guidance_on_valueerror(monkeypatch):
    message = DummyMessage("whatever")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    def fake_smart_input(_):
        raise ValueError("boom")

    monkeypatch.setattr(handlers, "smart_input", fake_smart_input)

    await handlers.freeform_handler(update, context)

    assert message.replies
    text, _ = message.replies[0]
    assert "Не удалось распознать значения" in text
