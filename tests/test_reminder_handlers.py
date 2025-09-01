import json
import importlib
import sys
from datetime import time, timedelta
from types import SimpleNamespace, TracebackType
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import Update, User
from telegram.ext import CallbackContext

from services.api.app.diabetes.utils.helpers import (
    INVALID_TIME_MSG,
    parse_time_interval,
)
from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    ReminderLog,
    User as DbUser,
)
from services.api.app.diabetes.services.repository import commit


@pytest.fixture
def reminder_handlers(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    config = importlib.import_module("services.api.app.config")
    importlib.reload(config)
    handlers = importlib.import_module(
        "services.api.app.diabetes.handlers.reminder_handlers",
    )
    importlib.reload(handlers)
    return handlers


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


class DummyWebAppData:
    def __init__(self, data: str) -> None:
        self.data = data


class DummyWebAppMessage(DummyMessage):
    def __init__(self, data: str) -> None:
        super().__init__()
        self.web_app_data = DummyWebAppData(data)


class DummyJobQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any, dict[str, Any] | None, str | None]] = []

    def run_once(
        self,
        callback: Any,
        when: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: object | None = None,
    ) -> None:
        self.calls.append((callback, when, data, name))

    def get_jobs_by_name(self, name: str) -> list[Any]:
        return []


def make_user(user_id: int) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_update(**kwargs: Any) -> Update:
    update = MagicMock(spec=Update)
    for key, value in kwargs.items():
        setattr(update, key, value)
    return cast(Update, update)


def make_context(
    **kwargs: Any,
) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    context = MagicMock(spec=CallbackContext)
    context.job_queue = None
    for key, value in kwargs.items():
        setattr(context, key, value)
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        context,
    )


@pytest.mark.asyncio
async def test_add_reminder_fewer_args(reminder_handlers: Any) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar"])

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Использование: /addreminder <type> <value>"]


@pytest.mark.asyncio
async def test_add_reminder_sugar_invalid_time(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "ab:cd"])

    parse_mock = MagicMock(side_effect=ValueError)
    monkeypatch.setattr(reminder_handlers, "parse_time_interval", parse_mock)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == [INVALID_TIME_MSG]
    parse_mock.assert_called_once_with("ab:cd")


@pytest.mark.asyncio
async def test_add_reminder_sugar_non_numeric_interval(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "abc"])

    parse_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "parse_time_interval", parse_mock)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Интервал должен быть числом."]
    parse_mock.assert_not_called()


@pytest.mark.asyncio
async def test_add_reminder_unknown_type(reminder_handlers: Any) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["unknown", "1"])

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Неизвестный тип напоминания."]


@pytest.mark.asyncio
async def test_add_reminder_valid_type(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "2"], job_queue=None)

    class DummyQuery:
        def filter_by(self, **kwargs: Any) -> "DummyQuery":
            return self

        def count(self) -> int:
            return 0

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        def query(self, *args: Any, **kwargs: Any) -> DummyQuery:
            return DummyQuery()

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def add(self, obj: Any) -> None:
            pass

    def session_factory() -> DummySession:
        return DummySession()

    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "commit", lambda s: None)
    monkeypatch.setattr(reminder_handlers, "_describe", lambda *a, **k: "desc")

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Сохранено: desc"]


@pytest.mark.asyncio
async def test_add_reminder_saves_time_and_description(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import datetime as dt

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    notify_mock = AsyncMock()
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=notify_mock),
    )

    class FixedDT(dt.datetime):
        @classmethod
        def now(cls, tz: dt.tzinfo | None = None) -> "FixedDT":
            return cls(2024, 1, 1, 8, 0, 0, tzinfo=tz)

    monkeypatch.setattr(reminder_handlers.datetime, "datetime", FixedDT)

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "09:00"])

    await reminder_handlers.add_reminder(update, context)

    notify_mock.assert_awaited_once_with(1)
    assert message.texts == ["Сохранено: 🔔 Замерить сахар ⏰ 09:00 (next 09:00)"]

    with TestSession() as session:
        rem_db = session.query(Reminder).one()
        assert rem_db.time == time(9, 0)


@pytest.mark.asyncio
async def test_add_reminder_no_broadcast_with_job_queue(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    schedule_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "schedule_reminder", schedule_mock)
    notify_mock = AsyncMock()
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=notify_mock),
    )
    monkeypatch.setattr(reminder_handlers, "_describe", lambda *a, **k: "desc")

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    job_queue = DummyJobQueue()
    context = make_context(args=["sugar", "09:00"], job_queue=job_queue)

    await reminder_handlers.add_reminder(update, context)

    schedule_mock.assert_called_once()
    notify_mock.assert_not_awaited()
    assert message.texts == ["Сохранено: desc"]


@pytest.mark.asyncio
async def test_add_reminder_ignores_disabled(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                telegram_id=1,
                type="sugar",
                interval_hours=2,
                is_enabled=False,
            )
        )
        commit(session)

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "2"], job_queue=None)

    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "_describe", lambda *a, **k: "desc")
    monkeypatch.setattr(reminder_handlers, "_limit_for", lambda u: 1)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Сохранено: desc"]


@pytest.mark.asyncio
async def test_delete_reminder_no_broadcast_with_job_queue(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
            )
        )
        session.commit()

    notify_mock = AsyncMock()
    monkeypatch.setattr(
        reminder_handlers.reminder_events, "notify_reminder_saved", notify_mock
    )

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    job_queue = DummyJobQueue()
    context = make_context(args=["1"], job_queue=job_queue)

    await reminder_handlers.delete_reminder(update, context)

    assert message.texts == ["Удалено"]
    notify_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_reminder_broadcasts_without_job_queue(
    reminder_handlers: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
            )
        )
        session.commit()

    notify_mock = AsyncMock()
    monkeypatch.setattr(
        reminder_handlers.reminder_events, "notify_reminder_saved", notify_mock
    )

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["1"], job_queue=None)

    await reminder_handlers.delete_reminder(update, context)

    assert message.texts == ["Удалено"]
    notify_mock.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_reminder_webapp_save_unknown_type(reminder_handlers: Any) -> None:
    message = DummyWebAppMessage(
        json.dumps({"type": "bad", "kind": "at_time", "time": "10:00"})
    )
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    assert message.texts == ["Неизвестный тип напоминания."]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [json.dumps({"id": 1, "snooze": 7}), "snooze=7&id=1"],
)
async def test_reminder_webapp_save_snooze(
    reminder_handlers: Any, payload: str
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    reminder_handlers.SessionLocal = TestSession
    reminder_handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    message = DummyWebAppMessage(payload)
    update = make_update(effective_message=message, effective_user=make_user(1))
    job_queue = DummyJobQueue()
    context = make_context(job_queue=job_queue)

    await reminder_handlers.reminder_webapp_save(update, context)

    assert message.texts == ["⏰ Отложено на 7 минут"]
    assert job_queue.calls
    callback, when, data, name = job_queue.calls[0]
    assert callback is reminder_handlers.reminder_job
    assert data == {"reminder_id": 1, "chat_id": 1}
    assert name == "reminder_1_snooze"
    assert when == timedelta(minutes=7)

    with TestSession() as session:
        log = session.query(ReminderLog).one()
        assert log.action == "snooze"
        assert log.reminder_id == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rtype,value",
    [("after_meal", "15"), ("custom", "09:00")],
)
async def test_reminder_webapp_save_clears_interval_params(
    reminder_handlers: Any,
    monkeypatch: pytest.MonkeyPatch,
    rtype: str,
    value: str,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(
        reminder_handlers, "_render_reminders", lambda s, uid: ("ok", None)
    )
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=AsyncMock()),
    )

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                interval_minutes=30,
                interval_hours=2,
            )
        )
        session.commit()

    if rtype == "after_meal":
        payload = {"id": 1, "type": rtype, "kind": "after_event", "minutesAfter": value}
    else:
        payload = {"id": 1, "type": rtype, "kind": "at_time", "time": value}
    message = DummyWebAppMessage(json.dumps(payload))
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
        assert rem_db is not None
        assert rem_db.interval_hours is None
        assert rem_db.interval_minutes is None
        if rtype == "after_meal":
            assert rem_db.kind == "after_event"
            assert rem_db.minutes_after == int(value)
            assert rem_db.time is None
        else:
            assert rem_db.kind == "at_time"
            assert rem_db.minutes_after is None
            parsed = parse_time_interval(value)
            assert isinstance(parsed, time)
            assert rem_db.time == parsed


@pytest.mark.asyncio
async def test_reminder_webapp_save_interval_minutes(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(
        reminder_handlers, "_render_reminders", lambda s, uid: ("ok", None)
    )
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=AsyncMock()),
    )

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyWebAppMessage(
        json.dumps({"type": "sugar", "kind": "every", "intervalMinutes": 90})
    )
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem_db = session.query(Reminder).one()
        assert rem_db.kind == "every"
        assert rem_db.interval_minutes == 90
        assert rem_db.interval_hours is None
        assert rem_db.time is None
        assert rem_db.minutes_after is None


@pytest.mark.asyncio
async def test_reminder_webapp_save_minutes_after(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(
        reminder_handlers, "_render_reminders", lambda s, uid: ("ok", None)
    )
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=AsyncMock()),
    )

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyWebAppMessage(
        json.dumps({"type": "after_meal", "kind": "after_event", "minutesAfter": 20})
    )
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem_db = session.query(Reminder).one()
        assert rem_db.kind == "after_event"
        assert rem_db.minutes_after == 20
        assert rem_db.time is None
        assert rem_db.interval_minutes is None
        assert rem_db.interval_hours is None


@pytest.mark.parametrize(
    "origin, ui_base, path",
    [
        ("https://example.com", "/ui", "/reminders/new"),
        ("https://example.com/", "ui/", "reminders/new"),
    ],
)
def test_build_ui_url(
    monkeypatch: pytest.MonkeyPatch, origin: str, ui_base: str, path: str
) -> None:
    expected = "https://example.com/ui/reminders/new"
    monkeypatch.setenv("PUBLIC_ORIGIN", origin)
    monkeypatch.setenv("UI_BASE_URL", ui_base)
    config = importlib.import_module("services.api.app.config")
    importlib.reload(config)
    try:
        url = config.build_ui_url(path)
        assert url == expected
        assert "//" not in url.split("://", 1)[1]
    finally:
        sys.modules.pop("services.api.app.config", None)


def test_build_ui_url_without_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_ORIGIN", "")
    monkeypatch.setenv("UI_BASE_URL", "")
    config = importlib.import_module("services.api.app.config")
    importlib.reload(config)
    with pytest.raises(RuntimeError, match="PUBLIC_ORIGIN not configured"):
        config.build_ui_url("/reminders/new")
    sys.modules.pop("services.api.app.config", None)
