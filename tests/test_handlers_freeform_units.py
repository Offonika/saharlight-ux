import pytest
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.dose_handlers as dose_handlers
from services.api.app.diabetes.handlers.dose_handlers import freeform_handler


class DummyMessage:
    def __init__(self, text: str):
        self.text = text
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


@pytest.mark.asyncio
async def test_freeform_handler_warns_on_sugar_unit_mix() -> None:
    message = DummyMessage("сахар 5 XE")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, Any, Any, Any], SimpleNamespace(user_data={})
    )

    await freeform_handler(update, context)

    assert message.replies
    text, _ = message.replies[0]
    assert "ммоль/л" in text and "Сахар" in text


@pytest.mark.asyncio
async def test_freeform_handler_warns_on_dose_unit_mix() -> None:
    message = DummyMessage("доза 7 ммоль")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, Any, Any, Any], SimpleNamespace(user_data={})
    )

    await freeform_handler(update, context)

    assert message.replies
    text, _ = message.replies[0]
    assert "ед" in text.lower() and "доза" in text.lower()


@pytest.mark.asyncio
async def test_freeform_handler_guidance_on_valueerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("whatever")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, Any, Any, Any], SimpleNamespace(user_data={})
    )

    def fake_smart_input(_):
        raise ValueError("boom")

    monkeypatch.setattr(dose_handlers, "smart_input", fake_smart_input)

    await freeform_handler(update, context)

    assert message.replies
    text, _ = message.replies[0]
    assert "Не удалось распознать значения" in text
