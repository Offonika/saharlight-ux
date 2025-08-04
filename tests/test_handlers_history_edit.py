import os
import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import InlineKeyboardMarkup

os.environ.setdefault("DB_PASSWORD", "test")
from diabetes.db import Base, User, Entry


class DummyMessage:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[tuple[str, dict]] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data: str):
        self.data = data
        self.edited: list[str] = []

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edited.append(text)


@pytest.mark.asyncio
async def test_history_view_buttons(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.openai_utils as openai_utils  # noqa: F401
    import diabetes.reporting_handlers as reporting_handlers
    import diabetes.common_handlers as common_handlers
    import diabetes.dose_handlers as dose_handlers

    engine = create_engine("sqlite:///:memory:")
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
            f"🍞 Углеводы: <b>— г (— ХЕ)</b>\n"
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
            carbs_g=10,
            xe=1,
            dose=2,
            sugar_before=5,
        )
        session.add(entry)
        session.commit()
        entry_id = entry.id

    query = DummyQuery(f"edit:{entry_id}")
    update_cb = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    await common_handlers.callback_router(update_cb, context)
    assert context.user_data.get("edit_id") == entry_id
    assert any("формате" in t for t in query.edited)

    msg = DummyMessage(text="xe=3 carbs=30 dose=1 sugar=6")
    update_msg = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))

    await dose_handlers.freeform_handler(update_msg, context)

    with TestSession() as session:
        updated = session.get(Entry, entry_id)
        assert updated.xe == 3
        assert updated.carbs_g == 30
        assert updated.dose == 1
        assert updated.sugar_before == 6

    assert "edit_id" not in context.user_data
    assert any("обновлена" in t[0] for t in msg.replies)
