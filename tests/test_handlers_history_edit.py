import os
import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from telegram import InlineKeyboardMarkup

os.environ.setdefault("DB_PASSWORD", "test")
from services.api.app.diabetes.services.db import Base, User, Entry


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
async def test_history_view_buttons(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers
    import services.api.app.diabetes.handlers.common_handlers as common_handlers
    import services.api.app.diabetes.handlers.dose_handlers as dose_handlers

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(reporting_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(common_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(dose_handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add_all(
            [
                Entry(
                    telegram_id=1,
                    event_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
                ),
                Entry(
                    telegram_id=1,
                    event_time=datetime.datetime(2024, 1, 2, tzinfo=datetime.timezone.utc),
                ),
            ]
        )
        session.commit()
        entry_ids = [e.id for e in session.query(Entry).all()]

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    await reporting_handlers.history_view(update, context)

    # First message is header, last is back button
    assert len(message.replies) == len(entry_ids) + 2
    all_callbacks = []
    expected_texts = []
    for d in [
        datetime.datetime(2024, 1, 2, tzinfo=datetime.timezone.utc),
        datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
    ]:
        day_str = d.strftime("%d.%m %H:%M")
        expected_texts.append(
            f"<b>{day_str}</b>\n"
            f"🍭 Сахар: <b>—</b>\n"
            f"🍞 Углеводы: <b>—</b>\n"
            f"💉 Доза: <b>—</b>"
        )
    for (text, kwargs), expected in zip(message.replies[1:-1], expected_texts):
        markup = kwargs.get("reply_markup")
        assert kwargs.get("parse_mode") == "HTML"
        assert text == expected
        assert isinstance(markup, InlineKeyboardMarkup)
        buttons = [b for row in markup.inline_keyboard for b in row]
        all_callbacks.extend(b.callback_data for b in buttons)
    for eid in entry_ids:
        assert f"edit:{eid}" in all_callbacks
        assert f"del:{eid}" in all_callbacks

    back_markup = message.replies[-1][1]["reply_markup"]
    back_button = back_markup.inline_keyboard[0][0]
    assert back_button.callback_data == "report_back"


@pytest.mark.asyncio
async def test_edit_flow(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.common_handlers as common_handlers
    import services.api.app.diabetes.handlers.dose_handlers as dose_handlers

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(common_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(dose_handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        entry = Entry(
            telegram_id=1,
            event_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            carbs_g=10,
            xe=1,
            dose=2,
            sugar_before=5,
        )
        session.add(entry)
        session.commit()
        entry_id = entry.id

    entry_message = DummyMessage(chat_id=42, message_id=24)
    query = DummyQuery(f"edit:{entry_id}", message=entry_message)
    update_cb = SimpleNamespace(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={}, bot=DummyBot())

    await common_handlers.callback_router(update_cb, context)
    assert context.user_data["edit_entry"] == {
        "id": entry_id,
        "chat_id": 42,
        "message_id": 24,
    }
    markup = query.markups[-1]
    buttons = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert f"edit_field:{entry_id}:sugar" in buttons
    assert f"edit_field:{entry_id}:xe" in buttons
    assert f"edit_field:{entry_id}:dose" in buttons

    field_query = DummyQuery(f"edit_field:{entry_id}:xe", message=entry_message)
    update_cb2 = SimpleNamespace(
        callback_query=field_query, effective_user=SimpleNamespace(id=1)
    )
    await common_handlers.callback_router(update_cb2, context)
    assert context.user_data["edit_id"] == entry_id
    assert context.user_data["edit_field"] == "xe"
    assert context.user_data["edit_query"] is field_query
    assert any("Введите" in t for t, _ in entry_message.replies)

    reply_msg = DummyMessage(text="3")
    update_msg = SimpleNamespace(
        message=reply_msg, effective_user=SimpleNamespace(id=1)
    )
    await dose_handlers.freeform_handler(update_msg, context)

    with TestSession() as session:
        updated = session.get(Entry, entry_id)
        assert updated.xe == 3
        assert updated.carbs_g == 10
        assert updated.dose == 2
        assert updated.sugar_before == 5

    assert field_query.answer_texts[-1] == "Изменено"
    assert not any(
        k in context.user_data for k in ("edit_id", "edit_field", "edit_entry", "edit_query")
    )
    edited_text, chat_id, message_id, kwargs = context.bot.edited[0]
    assert chat_id == 42 and message_id == 24
    buttons = [b.callback_data for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert f"edit:{entry_id}" in buttons and f"del:{entry_id}" in buttons
