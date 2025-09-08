import os
import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Chat, Message, Update
from telegram.ext import CallbackContext, ContextTypes
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers
from services.api.app.diabetes.handlers import UserData

os.environ.setdefault("DB_PASSWORD", "test")
from services.api.app.diabetes.services.db import Base, User, Entry


class DummyMessage(Message):
    __slots__ = ("replies", "kwargs")

    def __init__(self, text: str = "", chat_id: int = 1, message_id: int = 1) -> None:
        super().__init__(
            message_id=message_id,
            date=datetime.datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            text=text,
        )
        object.__setattr__(self, "replies", [])
        object.__setattr__(self, "kwargs", [])

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.data = data
        self.message = message
        self.markups: list[Any] = []
        self.answer_texts: list[str | None] = []

    async def answer(self, text: str | None = None) -> None:
        self.answer_texts.append(text)

    async def edit_message_reply_markup(
        self, reply_markup: Any | None = None, **kwargs: Any
    ) -> None:
        self.markups.append(reply_markup)


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
    import services.api.app.diabetes.handlers.dose_calc as dose_calc

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(router, "SessionLocal", TestSession)
    monkeypatch.setattr(dose_calc, "SessionLocal", TestSession)

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
    query = DummyQuery(entry_message, f"edit:{entry_id}")
    update_cb = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot=DummyBot()),
    )
    assert context.user_data is not None

    await router.callback_router(update_cb, context)

    field_query = DummyQuery(entry_message, f"edit_field:{entry_id}:dose")
    update_cb2 = cast(
        Update,
        SimpleNamespace(
            callback_query=field_query, effective_user=SimpleNamespace(id=1)
        ),
    )
    await router.callback_router(update_cb2, context)
    assert context.user_data is not None
    user_data = context.user_data
    assert user_data["edit_field"] == "dose"

    reply_msg = DummyMessage(text="5")
    update_msg = cast(
        Update, SimpleNamespace(message=reply_msg, effective_user=SimpleNamespace(id=1))
    )
    await dose_calc.freeform_handler(update_msg, context)

    with TestSession() as session:
        entry_obj = session.get(Entry, entry_id)
        assert entry_obj is not None
        entry_db: Entry = entry_obj
        assert entry_db.dose == 5.0
        day_str = entry_db.event_time.strftime("%d.%m %H:%M")

    edited_text, chat_id, message_id, kwargs = context.bot.edited[0]
    assert chat_id == 42 and message_id == 24
    assert f"<b>{day_str}</b>" in edited_text
    assert f"💉 Доза: <b>{entry_db.dose}</b>" in edited_text


@pytest.mark.asyncio
async def test_edit_dose_commit_failure() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

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

    message = DummyMessage(text="5", chat_id=42, message_id=24)
    user_data = cast(
        UserData,
        {
            "edit_id": entry_id,
            "edit_field": "dose",
            "edit_entry": {"chat_id": 42, "message_id": 24},
            "edit_query": {"chat_id": 42, "message_id": 24},
        },
    )
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        SimpleNamespace(bot=DummyBot()),
    )

    def commit_fail(session: Session) -> bool:
        raise gpt_handlers.CommitError

    result = await gpt_handlers._handle_edit_entry(
        "5",
        user_data,
        cast(Message, message),
        context,
        SessionLocal=TestSession,
        commit=commit_fail,
    )
    assert result is True
    assert message.replies[-1] == "⚠️ Не удалось сохранить запись."
    with TestSession() as session:
        entry_obj = session.get(Entry, entry_id)
        assert entry_obj is not None and entry_obj.dose == 2.0
