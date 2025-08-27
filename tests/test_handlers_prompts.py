import os
from types import SimpleNamespace
from typing import Any

import pytest
from tests.helpers import make_context, make_update

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
from services.api.app.diabetes.handlers import dose_handlers
from services.api.app.diabetes.utils.ui import sugar_keyboard


class DummyMessage:
    def __init__(self):
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_prompt_photo_sends_message() -> None:
    message = DummyMessage()
    update = make_update(message=message)
    await dose_handlers.prompt_photo(update, SimpleNamespace())
    assert any("фото" in t.lower() for t in message.texts)


@pytest.mark.asyncio
async def test_prompt_sugar_sends_message() -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=SimpleNamespace(id=1))
    context = make_context(user_data={})
    await dose_handlers.prompt_sugar(update, context)
    assert any("сахар" in t.lower() for t in message.texts)
    assert message.kwargs and message.kwargs[0].get("reply_markup") is sugar_keyboard


@pytest.mark.asyncio
async def test_prompt_dose_sends_message() -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=SimpleNamespace(id=1))
    context = make_context(user_data={})
    await dose_handlers.prompt_dose(update, context)
    assert any("доз" in t.lower() for t in message.texts)

