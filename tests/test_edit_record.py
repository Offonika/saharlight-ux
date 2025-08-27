import os
import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.helpers import make_update

os.environ.setdefault("DB_PASSWORD", "test")
from services.api.app.diabetes.services.db import Base, User, Entry


class DummyMessage:
    def __init__(self, text: str = "", chat_id: int = 1, message_id: int = 1) -> None:
        self.text = text
        self.chat_id = chat_id
        self.message_id = message_id
        self.replies: list[tuple[str, dict]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data: str, message: DummyMessage | None = None) -> None:
        self.data = data
        self.message = message or DummyMessage()
        self.markups = []
        self.answer_texts = []
        self.edited: list[str] = []

    async def answer(self, text: str | None = None) -> None:
        self.answer_texts.append(text)

    async def edit_message_reply_markup(
        self, reply_markup: Any | None = None, **kwargs: Any
    ) -> None:
        self.markups.append(reply_markup)

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


class DummyBot:
    def __init__(self) -> None:
        self.edited: list[tuple[str, int, int, dict[str, Any]]] = []

    async def edit_message_text(
        self, text: str, chat_id: int, message_id: int, **kwargs: Any
    ) -> None:
        self.edited.append((text, chat_id, message_id, kwargs))


@pytest.mark.asyncio
async def test_edit_dose(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router
    import services.api.app.diabetes.handlers.dose_handlers as dose_handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(router, "SessionLocal", TestSession)
    monkeypatch.setattr(dose_handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        entry = Entry(
            telegram_id=1,
            event_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            dose=2.0,
        )
        session.add(entry)
        session.commit()
        entry_id = entry.id

    entry_message = DummyMessage(chat_id=42, message_id=24)
    query = DummyQuery(f"edit:{entry_id}", message=entry_message)
    update_cb = make_update(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )
    context = cast(
        CallbackContext[Any, Any, Any, Any],
        SimpleNamespace(user_data={}, bot=DummyBot()),
    )

    await router.handle_edit_entry(update_cb, context)

    field_query = DummyQuery(f"edit_field:{entry_id}:dose", message=entry_message)
    update_cb2 = make_update(callback_query=field_query, effective_user=SimpleNamespace(id=1))
    await router.handle_edit_field(update_cb2, context)
    assert context.user_data["edit_field"] == "dose"

    reply_msg = DummyMessage(text="5")
    update_msg = cast(
        Update, SimpleNamespace(message=reply_msg, effective_user=SimpleNamespace(id=1))
    )
    await dose_handlers.freeform_handler(update_msg, context)

    with TestSession() as session:
        updated = session.get(Entry, entry_id)
        assert updated.dose == 5.0

    assert field_query.answer_texts[-1] == "Изменено"
    edited_text, chat_id, message_id, kwargs = context.bot.edited[0]
    assert chat_id == 42 and message_id == 24
    assert f"💉 Доза: <b>{updated.dose}</b>" in edited_text


@pytest.mark.asyncio
async def test_delete_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(router, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        entry = Entry(
            telegram_id=1,
            event_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        )
        session.add(entry)
        session.commit()
        entry_id = entry.id

    query = DummyQuery(f"del:{entry_id}")
    update = make_update(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace(user_data={}))

    await router.handle_delete_entry(update, context)

    with TestSession() as session:
        assert session.get(Entry, entry_id) is None
    assert query.edited == ["❌ Запись удалена."]
