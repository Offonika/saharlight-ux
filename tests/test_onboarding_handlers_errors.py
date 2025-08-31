from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_start_command_no_user() -> None:
    update = cast(Update, SimpleNamespace(message=None, effective_user=None))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    result = await onboarding.start_command(update, context)
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_onboarding_icr_invalid() -> None:
    message = DummyMessage("abc")
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    result = await onboarding.onboarding_icr(update, context)
    assert result == onboarding.ONB_PROFILE_ICR
    assert message.texts == ["Введите ИКХ числом."]


@pytest.mark.asyncio
async def test_onboarding_icr_non_positive() -> None:
    message = DummyMessage("0")
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    result = await onboarding.onboarding_icr(update, context)
    assert result == onboarding.ONB_PROFILE_ICR
    assert message.texts == ["ИКХ должен быть больше 0."]


@pytest.mark.asyncio
async def test_onboarding_cf_invalid() -> None:
    message = DummyMessage("abc")
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    result = await onboarding.onboarding_cf(update, context)
    assert result == onboarding.ONB_PROFILE_CF
    assert message.texts == ["Введите КЧ числом."]


@pytest.mark.asyncio
async def test_onboarding_target_missing_data() -> None:
    message = DummyMessage("5")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    result = await onboarding.onboarding_target(update, context)
    assert result == ConversationHandler.END
    assert message.texts == [
        "⚠️ Не хватает данных для профиля. Пожалуйста, начните заново."
    ]


@pytest.mark.asyncio
async def test_onboarding_demo_next_invalid_message_type() -> None:
    query = SimpleNamespace(message=object())
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )
    state = await onboarding.onboarding_demo_next(update, context)
    assert state == ConversationHandler.END


@pytest.mark.asyncio
async def test_onboarding_reminders_missing_message() -> None:
    class DummyQuery(SimpleNamespace):
        async def answer(self) -> None:
            pass

    query = DummyQuery(message=None, data="onb_rem_yes")
    update = cast(
        Update,
        SimpleNamespace(
            callback_query=query, effective_user=SimpleNamespace(id=1)
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}, job_queue=None),
    )
    state = await onboarding.onboarding_reminders(update, context)
    assert state == ConversationHandler.END


@pytest.mark.asyncio
async def test_onboarding_skip_missing_message() -> None:
    class DummyQuery(SimpleNamespace):
        async def answer(self) -> None:
            pass

    query = DummyQuery(message=None, data="onb_skip")
    update = cast(
        Update,
        SimpleNamespace(
            callback_query=query, effective_user=SimpleNamespace(id=1)
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )
    state = await onboarding.onboarding_skip(update, context)
    assert state == ConversationHandler.END

