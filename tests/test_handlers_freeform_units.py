import pytest
from types import SimpleNamespace
from typing import Any, cast, NoReturn

from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.dose_calc as handlers


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_freeform_handler_warns_on_sugar_unit_mix() -> None:
    message = DummyMessage("сахар 5 XE")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await handlers.freeform_handler(update, context)

    assert message.replies
    text = message.replies[0]
    assert "ммоль/л" in text and "Сахар" in text


@pytest.mark.asyncio
async def test_freeform_handler_warns_on_dose_unit_mix() -> None:
    message = DummyMessage("доза 7 ммоль")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await handlers.freeform_handler(update, context)

    assert message.replies
    text = message.replies[0]
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
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    def fake_smart_input(_: str) -> NoReturn:  # pragma: no cover
        raise ValueError("boom")

    monkeypatch.setattr(handlers, "smart_input", fake_smart_input)

    await handlers.freeform_handler(update, context)

    assert message.replies
    text = message.replies[0]
    assert "Не удалось распознать значения" in text