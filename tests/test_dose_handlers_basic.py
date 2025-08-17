from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest
from telegram import Update
from telegram.ext import ContextTypes
from typing import cast

from services.api.app.diabetes.handlers import dose_handlers


@dataclass
class DummyMessage:
    text: str | None = None
    reply_text: AsyncMock = field(default_factory=AsyncMock)


@dataclass
class DummyUpdate:
    message: DummyMessage | None = None


@dataclass
class DummyContext:
    user_data: dict[str, object]


@pytest.mark.asyncio
async def test_dose_start_clears_user_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    update = cast(Update, DummyUpdate(message=message))
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        DummyContext(user_data={"pending_entry": 1, "edit_id": 2, "dose_method": "xe"}),
    )
    monkeypatch.setattr(dose_handlers, "dose_keyboard", "kb")

    result = await dose_handlers.dose_start(update, context)

    assert context.user_data is not None
    user_data = cast(dict[str, object], context.user_data)
    assert user_data == {}
    message.reply_text.assert_awaited_once_with(
        "💉 Как рассчитать дозу? Выберите метод:", reply_markup="kb"
    )
    assert result == dose_handlers.DOSE_METHOD


@pytest.mark.asyncio
async def test_dose_method_choice_xe() -> None:
    message = DummyMessage(text="Xe")
    update = cast(Update, DummyUpdate(message=message))
    context = cast(ContextTypes.DEFAULT_TYPE, DummyContext(user_data={}))

    result = await dose_handlers.dose_method_choice(update, context)

    assert context.user_data is not None
    user_data = cast(dict[str, object], context.user_data)
    assert user_data["dose_method"] == "xe"
    message.reply_text.assert_awaited_once_with("Введите количество ХЕ.")
    assert result == dose_handlers.DOSE_XE

