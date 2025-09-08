import datetime
import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import (
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.ext import CallbackContext, ContextTypes
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("DB_PASSWORD", "test")
from services.api.app.diabetes.services.db import Base, User, Entry, HistoryRecord
from services.api.app.diabetes.handlers import UserData
import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers


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
    import services.api.app.diabetes.handlers.dose_calc as dose_calc
    import services.api.app.config as config

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(reporting_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(router, "SessionLocal", TestSession)
    monkeypatch.setattr(dose_calc, "SessionLocal", TestSession)
    monkeypatch.setattr(config.settings, "public_origin", "")

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add_all(
            [
                HistoryRecord(
                    id="1",
                    telegram_id=1,
                    date=datetime.date(2024, 1, 1),
                    time=datetime.time(0, 0),
                    type="meal",
                ),
                HistoryRecord(
                    id="2",
                    telegram_id=1,
                    date=datetime.date(2024, 1, 2),
                    time=datetime.time(0, 0),
                    type="meal",
                ),
            ]
        )
        session.commit()
        entry_ids = [r.id for r in session.query(HistoryRecord).all()]

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
            f"<b>{day_str}</b>\n🍭 Сахар: <b>—</b>\n🍞 Углеводы: <b>—</b>\n💉 Доза: <b>—</b>"
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
async def test_history_view_webapp_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers
    from services.api.app import config

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reporting_handlers, "SessionLocal", TestSession)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            HistoryRecord(
                id="1",
                telegram_id=1,
                date=datetime.date(2024, 1, 1),
                time=datetime.time(0, 0),
                type="meal",
            )
        )
        session.commit()

    monkeypatch.setattr(config.settings, "public_origin", "https://example.com")

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

    assert len(message.replies) == 4
    webapp_kwargs = message.kwargs[1]
    markup = webapp_kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    button = markup.inline_keyboard[0][0]
    assert button.text == "🌐 Открыть историю в WebApp"
    assert button.web_app is not None
    assert button.web_app.url == config.build_ui_url("/history?limit=10")


@pytest.mark.asyncio
async def test_edit_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router
    import services.api.app.diabetes.handlers.dose_calc as dose_calc

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(router, "SessionLocal", TestSession)
    monkeypatch.setattr(dose_calc, "SessionLocal", TestSession)

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
        SimpleNamespace(
            callback_query=field_query, effective_user=SimpleNamespace(id=1)
        ),
    )
    await router.callback_router(update_cb2, context)
    assert context.user_data is not None
    user_data = context.user_data
    assert user_data["edit_id"] == entry_id
    assert user_data["edit_field"] == "xe"
    assert user_data["edit_query"] == {"chat_id": 42, "message_id": 24}
    assert any("Введите" in t for t in entry_message.replies)

    reply_msg = DummyMessage(text="3")
    update_msg = cast(
        Update,
        SimpleNamespace(message=reply_msg, effective_user=SimpleNamespace(id=1)),
    )
    await dose_calc.freeform_handler(update_msg, context)

    with TestSession() as session:
        entry_obj = session.get(Entry, entry_id)
        assert entry_obj is not None
        entry_db: Entry = entry_obj
        assert entry_db.xe == 3
        assert entry_db.carbs_g == 10
        assert entry_db.dose == 2
        assert entry_db.sugar_before == 5

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


@pytest.mark.asyncio
async def test_handle_edit_entry_missing_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        entry = Entry(
            telegram_id=1,
            event_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            xe=1,
        )
        session.add(entry)
        session.commit()
        entry_id = entry.id

    user_data = cast(UserData, {"edit_id": entry_id, "edit_field": "xe"})
    message = cast(Message, DummyMessage(text="2"))
    context = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace(bot=DummyBot()))

    def commit_fn(session: Session) -> bool:
        session.commit()
        return True

    result = await gpt_handlers._handle_edit_entry(
        "2",
        user_data,
        message,
        context,
        SessionLocal=TestSession,
        commit=commit_fn,
    )

    assert result is False
    assert not any(
        k in user_data for k in ("edit_id", "edit_field", "edit_entry", "edit_query")
    )
    with TestSession() as session:
        entry_obj = session.get(Entry, entry_id)
        assert entry_obj is not None
        assert entry_obj.xe == 2
