import os
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.handlers.sugar_handlers as sugar_handlers
from services.api.app.diabetes.handlers import dose_calc
from services.api.app.diabetes.utils.ui import sugar_keyboard


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_prompt_photo_sends_message() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    await photo_handlers.prompt_photo(
        update,
        cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            SimpleNamespace(),
        ),
    )
    assert any("фото" in t.lower() for t in message.texts)


@pytest.mark.asyncio
async def test_prompt_sugar_sends_message() -> None:
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await sugar_handlers.prompt_sugar(update, context)
    assert any("сахар" in t.lower() for t in message.texts)
    assert message.kwargs and message.kwargs[0].get("reply_markup") is sugar_keyboard


@pytest.mark.asyncio
async def test_prompt_dose_sends_message() -> None:
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await dose_calc.prompt_dose(update, context)
    assert any("доз" in t.lower() for t in message.texts)
