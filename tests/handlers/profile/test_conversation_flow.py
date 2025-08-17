import importlib
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from unittest.mock import AsyncMock

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []
        self.markups: list[Any] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.markups.append(kwargs.get("reply_markup"))

    async def delete(self) -> None:  # pragma: no cover - interface completeness
        pass


@pytest.mark.asyncio
async def test_profile_edit_prompts() -> None:
    message = DummyMessage()
    query = SimpleNamespace(message=message, answer=AsyncMock())
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    state = await handlers.profile_edit(update, context)

    assert state == handlers.PROFILE_ICR
    assert "Введите коэффициент ИКХ" in message.replies[0]
    assert message.markups[0] is handlers.back_keyboard


@pytest.mark.asyncio
async def test_profile_creation_flow_success(monkeypatch: pytest.MonkeyPatch) -> None:
    run_db_mock = AsyncMock(return_value=True)
    session_local_mock = object()
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    monkeypatch.setattr(handlers, "SessionLocal", session_local_mock)

    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    user = SimpleNamespace(id=1)

    # ICR step
    msg1 = DummyMessage("8")
    upd1 = cast(Update, SimpleNamespace(message=msg1, effective_user=user))
    state = await handlers.profile_icr(upd1, ctx)
    assert state == handlers.PROFILE_CF
    assert "коэффициент чувствительности" in msg1.replies[0]

    # CF step
    msg2 = DummyMessage("3")
    upd2 = cast(Update, SimpleNamespace(message=msg2, effective_user=user))
    state = await handlers.profile_cf(upd2, ctx)
    assert state == handlers.PROFILE_TARGET
    assert "целевой уровень сахара" in msg2.replies[0]

    # Target step
    msg3 = DummyMessage("6")
    upd3 = cast(Update, SimpleNamespace(message=msg3, effective_user=user))
    state = await handlers.profile_target(upd3, ctx)
    assert state == handlers.PROFILE_LOW
    assert "нижний порог" in msg3.replies[0]

    # Low step
    msg4 = DummyMessage("4")
    upd4 = cast(Update, SimpleNamespace(message=msg4, effective_user=user))
    state = await handlers.profile_low(upd4, ctx)
    assert state == handlers.PROFILE_HIGH
    assert "верхний порог" in msg4.replies[0]

    # High step -> save profile
    msg5 = DummyMessage("9")
    upd5 = cast(Update, SimpleNamespace(message=msg5, effective_user=user))
    state = await handlers.profile_high(upd5, ctx)
    assert state == handlers.END
    assert any("Профиль обновлён" in r for r in msg5.replies)
    run_db_mock.assert_awaited_once()
    assert run_db_mock.await_args is not None
    assert (
        run_db_mock.await_args.kwargs["sessionmaker"] is session_local_mock
    )


@pytest.mark.asyncio
async def test_profile_creation_db_error(monkeypatch: pytest.MonkeyPatch) -> None:
    run_db_mock = AsyncMock(return_value=False)
    session_local_mock = object()
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    monkeypatch.setattr(handlers, "SessionLocal", session_local_mock)

    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={
                "profile_icr": 8.0,
                "profile_cf": 3.0,
                "profile_target": 6.0,
                "profile_low": 4.0,
            }
        ),
    )
    user = SimpleNamespace(id=1)
    msg = DummyMessage("9")
    upd = cast(Update, SimpleNamespace(message=msg, effective_user=user))

    state = await handlers.profile_high(upd, ctx)

    assert state == handlers.END
    assert msg.replies[0] == "⚠️ Не удалось сохранить профиль."
    run_db_mock.assert_awaited_once()
    assert run_db_mock.await_args is not None
    assert (
        run_db_mock.await_args.kwargs["sessionmaker"] is session_local_mock
    )


@pytest.mark.asyncio
async def test_profile_icr_invalid() -> None:
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    user = SimpleNamespace(id=1)
    msg = DummyMessage("abc")
    upd = cast(Update, SimpleNamespace(message=msg, effective_user=user))

    state = await handlers.profile_icr(upd, ctx)

    assert state == handlers.PROFILE_ICR
    assert "Введите ИКХ числом" in msg.replies[0]

