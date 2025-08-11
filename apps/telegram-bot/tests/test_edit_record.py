import os
import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_PASSWORD", "test")
from diabetes.db import Base, User, Entry


class DummyMessage:
    def __init__(self, text: str = "", chat_id: int = 1, message_id: int = 1):
        self.text = text
        self.chat_id = chat_id
        self.message_id = message_id
        self.replies: list[tuple[str, dict]] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data: str, message: DummyMessage | None = None):
        self.data = data
        self.message = message or DummyMessage()
        self.markups = []
        self.answer_texts = []

    async def answer(self, text=None):
        self.answer_texts.append(text)

    async def edit_message_reply_markup(self, reply_markup=None, **kwargs):
        self.markups.append(reply_markup)


class DummyBot:
    def __init__(self):
        self.edited: list[tuple[str, int, int, dict]] = []

    async def edit_message_text(self, text, chat_id, message_id, **kwargs):
        self.edited.append((text, chat_id, message_id, kwargs))


@pytest.mark.asyncio
async def test_edit_dose(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.openai_utils as openai_utils  # noqa: F401
    import diabetes.common_handlers as common_handlers
    import diabetes.dose_handlers as dose_handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(common_handlers, "SessionLocal", TestSession)
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
    update_cb = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={}, bot=DummyBot())

    await common_handlers.callback_router(update_cb, context)

    field_query = DummyQuery(f"edit_field:{entry_id}:dose", message=entry_message)
    update_cb2 = SimpleNamespace(callback_query=field_query, effective_user=SimpleNamespace(id=1))
    await common_handlers.callback_router(update_cb2, context)
    assert context.user_data["edit_field"] == "dose"

    reply_msg = DummyMessage(text="5")
    update_msg = SimpleNamespace(message=reply_msg, effective_user=SimpleNamespace(id=1))
    await dose_handlers.freeform_handler(update_msg, context)

    with TestSession() as session:
        updated = session.get(Entry, entry_id)
        assert updated.dose == 5.0

    assert field_query.answer_texts[-1] == "Изменено"
    edited_text, chat_id, message_id, kwargs = context.bot.edited[0]
    assert chat_id == 42 and message_id == 24
    assert f"💉 Доза: <b>{updated.dose}</b>" in edited_text
