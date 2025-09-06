import json
import importlib
import logging
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
async def test_add_reminder_sugar_invalid_time(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "ab:cd"])

    parse_mock = MagicMock(side_effect=ValueError)
    monkeypatch.setattr(reminder_handlers, "parse_time_interval", parse_mock)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == [INVALID_TIME_MSG]
    parse_mock.assert_called_once_with("ab:cd")


@pytest.mark.asyncio
async def test_add_reminder_sugar_non_numeric_interval(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
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
async def test_add_reminder_valid_type(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
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

        def execute(self, *args: Any, **kwargs: Any) -> Any:
            class R:
                def scalar_one(self) -> int:
                    return 0

            return R()

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
async def test_add_reminder_saves_time_and_description(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    import datetime as dt

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
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
        assert rem_db.kind == "at_time"
        assert rem_db.interval_hours is None
        assert rem_db.interval_minutes is None
        assert rem_db.minutes_after is None


@pytest.mark.asyncio
async def test_add_reminder_interval_sets_every_and_logs(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import datetime as dt

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
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
    context = make_context(args=["sugar", "3"])

    with caplog.at_level(logging.DEBUG):
        await reminder_handlers.add_reminder(update, context)

    notify_mock.assert_awaited_once_with(1)
    assert message.texts == ["Сохранено: 🔔 Замерить сахар ⏱ каждые 3 ч (next 11:00)"]
    assert any("kind=every" in rec.message and "interval_minutes=180" in rec.message for rec in caplog.records)

    with TestSession() as session:
        rem_db = session.query(Reminder).one()
        assert rem_db.kind == "every"
        assert rem_db.interval_hours == 3
        assert rem_db.interval_minutes == 180
        assert rem_db.time is None
        assert rem_db.minutes_after is None


@pytest.mark.asyncio
async def test_add_reminder_after_meal_sets_kind(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
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

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["after_meal", "15"])

    await reminder_handlers.add_reminder(update, context)

    notify_mock.assert_awaited_once_with(1)

    with TestSession() as session:
        rem_db = session.query(Reminder).one()
        assert rem_db.kind == "after_event"
        assert rem_db.minutes_after == 15
        assert rem_db.time is None
        assert rem_db.interval_minutes is None
        assert rem_db.interval_hours is None


@pytest.mark.asyncio
async def test_add_reminder_after_meal_requires_value(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["after_meal"])

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Использование: /addreminder <type> <value>"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rtype",
    [
        "insulin_short",
        "insulin_long",
        "meal",
        "sensor_change",
        "injection_site",
        "custom",
    ],
)
async def test_add_reminder_other_types_at_time(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch, rtype: str
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
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

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=[rtype, "09:00"])

    await reminder_handlers.add_reminder(update, context)

    notify_mock.assert_awaited_once_with(1)

    with TestSession() as session:
        rem_db = session.query(Reminder).one()
        assert rem_db.kind == "at_time"
        assert rem_db.time == time(9, 0)
        assert rem_db.interval_minutes is None
        assert rem_db.interval_hours is None
        assert rem_db.minutes_after is None


@pytest.mark.asyncio
async def test_add_reminder_no_broadcast_with_job_queue(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
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
async def test_add_reminder_ignores_disabled(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(reminder_handlers.reminder_events, "notify_reminder_saved", notify_mock)

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
    monkeypatch.setattr(reminder_handlers.reminder_events, "notify_reminder_saved", notify_mock)

    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["1"], job_queue=None)

    await reminder_handlers.delete_reminder(update, context)

    assert message.texts == ["Удалено"]
    notify_mock.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_reminder_webapp_save_unknown_type(reminder_handlers: Any) -> None:
    message = DummyWebAppMessage(json.dumps({"type": "bad", "kind": "at_time", "time": "10:00"}))
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    assert message.texts == ["Неизвестный тип напоминания."]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [json.dumps({"id": 1, "snooze": 7}), "snooze=7&id=1"],
)
async def test_reminder_webapp_save_snooze(reminder_handlers: Any, payload: str) -> None:
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
    monkeypatch.setattr(reminder_handlers, "_render_reminders", lambda s, uid: ("ok", None))
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
async def test_reminder_webapp_save_interval_minutes(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "_render_reminders", lambda s, uid: ("ok", None))
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=AsyncMock()),
    )

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyWebAppMessage(json.dumps({"type": "sugar", "kind": "every", "intervalMinutes": 90}))
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
async def test_reminder_webapp_save_minutes_after(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "_render_reminders", lambda s, uid: ("ok", None))
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=AsyncMock()),
    )

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyWebAppMessage(json.dumps({"type": "after_meal", "kind": "after_event", "minutesAfter": 20}))
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


@pytest.mark.asyncio
async def test_reminder_webapp_save_minutes_after_required(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(reminder_handlers, "commit", commit)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "_render_reminders", lambda s, uid: ("ok", None))
    monkeypatch.setattr(
        reminder_handlers,
        "reminder_events",
        SimpleNamespace(notify_reminder_saved=AsyncMock()),
    )

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyWebAppMessage(json.dumps({"type": "after_meal"}))
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    assert message.texts == ["Неверный формат"]
    with TestSession() as session:
        assert session.query(Reminder).count() == 0


@pytest.mark.parametrize(
    "origin, ui_base, path",
    [
        ("https://example.com", "/ui", "/reminders/new"),
        ("https://example.com/", "ui/", "reminders/new"),
    ],
)
def test_build_ui_url(monkeypatch: pytest.MonkeyPatch, origin: str, ui_base: str, path: str) -> None:
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


@pytest.mark.asyncio
async def test_reminder_action_not_found(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    query = MagicMock()
    query.data = "rem_toggle:1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=None)

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:  # pragma: no cover - no cleanup
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return None

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(reminder_handlers, "run_db", None)

    await reminder_handlers.reminder_action_cb(update, context)

    query.answer.assert_awaited_once_with("Не найдено", show_alert=True)


@pytest.mark.asyncio
async def test_reminder_action_unknown(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    query = MagicMock()
    query.data = "rem_foo:1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=None)

    class Rem:
        telegram_id = 1

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:  # pragma: no cover
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return Rem()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(reminder_handlers, "run_db", None)

    await reminder_handlers.reminder_action_cb(update, context)

    query.answer.assert_awaited_once_with("Неизвестное действие", show_alert=True)


@pytest.mark.asyncio
async def test_reminder_action_commit_error(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    query = MagicMock()
    query.data = "rem_toggle:1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=None)

    class Rem:
        telegram_id = 1
        is_enabled = False

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:  # pragma: no cover
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return Rem()

        def refresh(self, rem: Any) -> None:  # pragma: no cover - not called on error
            pass

    def raise_commit(session: Any) -> None:
        raise reminder_handlers.CommitError

    monkeypatch.setattr(reminder_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "commit", raise_commit)

    await reminder_handlers.reminder_action_cb(update, context)

    query.answer.assert_not_called()


@pytest.mark.asyncio
async def test_reminder_action_delete(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    query = MagicMock()
    query.data = "rem_del:1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=None)

    class Rem:
        telegram_id = 1

    class DummySession:
        def __init__(self) -> None:
            self.deleted = False

        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:  # pragma: no cover
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return Rem()

        def delete(self, obj: Any) -> None:
            self.deleted = True

        def refresh(self, rem: Any) -> None:  # pragma: no cover - not used
            pass

    sessions: list[DummySession] = []

    def session_factory() -> DummySession:
        sess = DummySession()
        sessions.append(sess)
        return sess

    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "commit", lambda s: None)
    monkeypatch.setattr(
        reminder_handlers.reminder_events,
        "notify_reminder_saved",
        AsyncMock(),
    )
    monkeypatch.setattr(reminder_handlers, "_render_reminders", lambda s, u: ("ok", None))

    await reminder_handlers.reminder_action_cb(update, context)

    assert sessions[0].deleted is True
    reminder_handlers.reminder_events.notify_reminder_saved.assert_awaited_once_with(1)
    query.answer.assert_awaited_once_with("Готово ✅")


@pytest.mark.asyncio
async def test_reminder_action_toggle(reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    query = MagicMock()
    query.data = "rem_toggle:1"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=None)

    class Rem:
        telegram_id = 1
        is_enabled = False

    rem_instance = Rem()

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:  # pragma: no cover
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return rem_instance

        def delete(self, obj: Any) -> None:  # pragma: no cover - not used
            pass

        def refresh(self, rem: Rem) -> None:
            pass

    def session_factory() -> DummySession:
        return DummySession()

    notify_mock = AsyncMock()

    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "commit", lambda s: None)
    monkeypatch.setattr(
        reminder_handlers.reminder_events,
        "notify_reminder_saved",
        notify_mock,
    )
    monkeypatch.setattr(reminder_handlers, "_render_reminders", lambda s, u: ("ok", None))

    await reminder_handlers.reminder_action_cb(update, context)

    assert rem_instance.is_enabled is True
    notify_mock.assert_awaited_once_with(1)
    query.answer.assert_awaited_once_with("Готово ✅")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,rtype,title,hour",
    [
        ("sugar_08", "sugar", None, 8),
        ("long_22", "insulin_long", None, 22),
        ("pills_09", "custom", "Таблетки", 9),
    ],
)
async def test_create_reminder_from_preset_schedules(
    reminder_handlers: Any,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    rtype: str,
    title: str | None,
    hour: int,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
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

    jq = DummyJobQueue()
    rem = await reminder_handlers.create_reminder_from_preset(1, code, jq)

    assert rem is not None
    assert rem.type == rtype
    assert rem.time == time(hour, 0)
    if title is not None:
        assert rem.title == title
    schedule_mock.assert_called_once()
    notify_mock.assert_not_awaited()
    with TestSession() as session:
        assert session.query(Reminder).count() == 1


@pytest.mark.asyncio
async def test_create_reminder_from_preset_no_queue_and_duplicate(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
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

    first = await reminder_handlers.create_reminder_from_preset(1, "sugar_08", None)
    second = await reminder_handlers.create_reminder_from_preset(1, "sugar_08", None)

    assert first is not None
    assert second is None
    schedule_mock.assert_not_called()
    notify_mock.assert_awaited_once_with(first.id)
    with TestSession() as session:
        assert session.query(Reminder).count() == 1
