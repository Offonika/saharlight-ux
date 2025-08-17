from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.diabetes.handlers.dose_handlers as dose_handlers
from services.api.app.diabetes.services.db import Base, Entry


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_photo_prompt_sends_message() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await dose_handlers.photo_prompt(update, context)
    assert any("фото" in r.lower() for r in message.replies)


@pytest.mark.asyncio
async def test_sugar_start_initializes_pending_entry() -> None:
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, chat_data={}),
    )
    state = await dose_handlers.sugar_start(update, context)
    assert state == dose_handlers.SUGAR_VAL
    assert context.user_data is not None
    assert context.user_data["pending_entry"]["telegram_id"] == 1
    assert context.chat_data is not None
    assert context.chat_data["sugar_active"]


@pytest.mark.asyncio
async def test_sugar_val_non_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    start_msg = DummyMessage()
    start_update = cast(
        Update, SimpleNamespace(message=start_msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, chat_data={}),
    )
    await dose_handlers.sugar_start(start_update, context)

    def fail_session() -> Any:
        raise AssertionError("DB should not be used")

    monkeypatch.setattr(dose_handlers, "SessionLocal", fail_session)

    called = False

    async def fake_check_alert(*args: Any, **kwargs: Any) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(dose_handlers, "check_alert", fake_check_alert)

    message = DummyMessage("abc")
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    result = await dose_handlers.sugar_val(update, context)
    assert result == dose_handlers.SUGAR_VAL
    assert message.replies[-1] == "Введите сахар числом в ммоль/л."
    assert not called


@pytest.mark.asyncio
async def test_sugar_val_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    start_msg = DummyMessage()
    start_update = cast(
        Update, SimpleNamespace(message=start_msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, chat_data={}),
    )
    await dose_handlers.sugar_start(start_update, context)

    def fail_session() -> Any:
        raise AssertionError("DB should not be used")

    monkeypatch.setattr(dose_handlers, "SessionLocal", fail_session)

    called = False

    async def fake_check_alert(*args: Any, **kwargs: Any) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(dose_handlers, "check_alert", fake_check_alert)

    message = DummyMessage("-1")
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    result = await dose_handlers.sugar_val(update, context)
    assert result == dose_handlers.SUGAR_VAL
    assert message.replies[-1] == "Сахар не может быть отрицательным."
    assert not called


@pytest.mark.asyncio
async def test_sugar_val_valid_saves_and_alerts(monkeypatch: pytest.MonkeyPatch) -> None:
    start_msg = DummyMessage()
    start_update = cast(
        Update, SimpleNamespace(message=start_msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, chat_data={}),
    )
    await dose_handlers.sugar_start(start_update, context)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(dose_handlers, "SessionLocal", session_factory)

    captured: dict[str, float] = {}

    async def fake_check_alert(update: Update, ctx: Any, sugar: float) -> None:
        captured["value"] = sugar

    monkeypatch.setattr(dose_handlers, "check_alert", fake_check_alert)

    message = DummyMessage("5.5")
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    result = await dose_handlers.sugar_val(update, context)
    assert result == dose_handlers.END
    assert captured["value"] == 5.5
    assert any("сохран" in r.lower() for r in message.replies)

    with session_factory() as session:
        entries = session.execute(select(Entry)).scalars().all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.sugar_before == 5.5
        assert entry.telegram_id == 1
