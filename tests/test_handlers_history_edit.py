import datetime
import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DB_PASSWORD", "test")
from services.api.app.diabetes.services.db import Base, User, Entry


class DummyMessage:
    def __init__(self, text: str = "", chat_id: int = 1, message_id: int = 1) -> None:
        self.text: str = text
        self.chat_id: int = chat_id
        self.message_id: int = message_id
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.data = data
        self.message = message
        self.markups: list[Any | None] = []
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
async def test_history_view_buttons(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers
    import services.api.app.diabetes.handlers.router as router
    import services.api.app.diabetes.handlers.dose_handlers as dose_handlers

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(reporting_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(router, "SessionLocal", TestSession)
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
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await reporting_handlers.history_view(update, context)

    # First message is header, last is back button
    assert len(message.replies) == len(entry_ids) + 2
    all_callbacks: list[str] = []
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
    for text, kwargs, expected in zip(
        message.replies[1:-1], message.kwargs[1:-1], expected_texts
    ):
        markup = kwargs.get("reply_markup")
        assert kwargs.get("parse_mode") == "HTML"
        assert text == expected
        assert isinstance(markup, InlineKeyboardMarkup)
        buttons: list[InlineKeyboardButton] = [
            b for row in markup.inline_keyboard for b in row
        ]
        all_callbacks.extend(
            [cast(str, b.callback_data) for b in buttons if b.callback_data is not None]
        )
    for eid in entry_ids:
        assert f"edit:{eid}" in all_callbacks
        assert f"del:{eid}" in all_callbacks

    back_kwargs = message.kwargs[-1]
    back_markup = back_kwargs.get("reply_markup")
    assert isinstance(back_markup, InlineKeyboardMarkup)
    back_button = back_markup.inline_keyboard[0][0]
    assert back_button.callback_data == "report_back"


@pytest.mark.asyncio
async def test_edit_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router
    import services.api.app.diabetes.handlers.dose_handlers as dose_handlers

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(router, "SessionLocal", TestSession)
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
    assert context.user_data is not None
    user_data = context.user_data
    assert user_data["edit_entry"] == {
        "id": entry_id,
        "chat_id": 42,
        "message_id": 24,
    }
    markup = query.markups[-1]
    assert markup is not None
    buttons = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert f"edit_field:{entry_id}:sugar" in buttons
    assert f"edit_field:{entry_id}:xe" in buttons
    assert f"edit_field:{entry_id}:dose" in buttons

    field_query = DummyQuery(entry_message, f"edit_field:{entry_id}:xe")
    update_cb2 = cast(
        Update,
        SimpleNamespace(callback_query=field_query, effective_user=SimpleNamespace(id=1)),
    )
    await router.callback_router(update_cb2, context)
    assert context.user_data is not None
    user_data = context.user_data
    assert user_data["edit_id"] == entry_id
    assert user_data["edit_field"] == "xe"
    assert user_data["edit_query"] is field_query
    assert any("Введите" in t for t in entry_message.replies)

    reply_msg = DummyMessage(text="3")
    update_msg = cast(
        Update,
        SimpleNamespace(message=reply_msg, effective_user=SimpleNamespace(id=1)),
    )
    await dose_handlers.freeform_handler(update_msg, context)

    with TestSession() as session:
        entry_obj = session.get(Entry, entry_id)
        assert entry_obj is not None
        entry_db: Entry = entry_obj
        assert entry_db.xe == 3
        assert entry_db.carbs_g == 10
        assert entry_db.dose == 2
        assert entry_db.sugar_before == 5

    assert field_query.answer_texts[-1] == "Изменено"
    assert context.user_data is not None
    user_data = context.user_data
    assert not any(
        k in user_data for k in ("edit_id", "edit_field", "edit_entry", "edit_query")
    )
    edited_text, chat_id, message_id, kwargs = context.bot.edited[0]
    assert chat_id == 42 and message_id == 24
    reply_markup = kwargs.get("reply_markup")
    assert reply_markup is not None
    buttons = [b.callback_data for row in reply_markup.inline_keyboard for b in row]
    assert f"edit:{entry_id}" in buttons and f"del:{entry_id}" in buttons
