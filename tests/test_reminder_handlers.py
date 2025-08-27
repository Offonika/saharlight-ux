import json
import importlib
from datetime import time, timedelta
from types import TracebackType
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update, User
from telegram.ext import CallbackContext

from services.api.app.diabetes.utils.helpers import INVALID_TIME_MSG
from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    ReminderLog,
    User as DbUser,
)
from services.api.app.diabetes.services.repository import commit
import services.api.app.config as config


@pytest.fixture
def reminder_handlers(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    importlib.reload(config)
    import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers

    return reminder_handlers


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
    ) -> None:
        self.calls.append((callback, when, data, name))


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
async def test_reminder_webapp_save_unknown_type(reminder_handlers: Any) -> None:
    message = DummyWebAppMessage(json.dumps({"type": "bad", "value": "10:00"}))
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
    assert name == "reminder_1"
    assert when == timedelta(minutes=7)

    with TestSession() as session:
        log = session.query(ReminderLog).one()
        assert log.action == "snooze"
        assert log.reminder_id == 1

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
    importlib.reload(config)
    url = config.build_ui_url(path)
    assert url == expected
    assert "//" not in url.split("://", 1)[1]


def test_build_ui_url_without_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    monkeypatch.delenv("UI_BASE_URL", raising=False)
    importlib.reload(config)
    with pytest.raises(RuntimeError, match="PUBLIC_ORIGIN not configured"):
        config.build_ui_url("/reminders/new")
