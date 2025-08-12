from types import SimpleNamespace
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import apps.telegram_bot.openai_utils as openai_utils  # noqa: F401
from apps.telegram_bot import dose_handlers
from apps.telegram_bot.ui import sugar_keyboard


class DummyMessage:
    def __init__(self):
        self.texts: list[str] = []
        self.kwargs: list[dict] = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_prompt_photo_sends_message():
    message = DummyMessage()
    update = SimpleNamespace(message=message)
    await dose_handlers.prompt_photo(update, SimpleNamespace())
    assert any("фото" in t.lower() for t in message.texts)


@pytest.mark.asyncio
async def test_prompt_sugar_sends_message():
    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})
    await dose_handlers.prompt_sugar(update, context)
    assert any("сахар" in t.lower() for t in message.texts)
    assert message.kwargs and message.kwargs[0].get("reply_markup") is sugar_keyboard


@pytest.mark.asyncio
async def test_prompt_dose_sends_message():
    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})
    await dose_handlers.prompt_dose(update, context)
    assert any("доз" in t.lower() for t in message.texts)

