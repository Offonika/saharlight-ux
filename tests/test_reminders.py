import json
import logging
from collections.abc import Generator
from datetime import datetime, time, timezone, tzinfo
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock
from typing import Any, Callable, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import Message, Update, User
from telegram.ext import CallbackContext, Job

from services.api.app.config import settings
import services.api.app.diabetes.handlers.reminder_handlers as handlers
import services.api.app.diabetes.handlers.router as router
from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    ReminderLog,
    User as DbUser,
)
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.helpers import parse_time_interval
from services.api.app.routers.reminders import router as reminders_router
from services.api.app.services import reminders
from services.api.app.telegram_auth import require_tg_user

# Ensure handlers use current settings after config reloads
handlers.settings = settings

class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text: str | None = text
        self.texts: list[str] = []
        self.edited: tuple[str, dict[str, Any]] | None = None
        self.kwargs: list[dict[str, Any]] = []
        self.web_app_data: Any | None = None

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)

    async def edit_text(self, text: str, **kwargs: Any) -> None:
        self.edited = (text, kwargs)


class DummyCallbackQuery:
    def __init__(self, data: str, message: DummyMessage, id: str = "1") -> None:
        self.data = data
        self.message = message
        self.id = id
        self.answers: list[str | None] = []
        self.edited: tuple[str, dict[str, Any]] | None = None

    async def answer(self, text: str | None = None, **kwargs: Any) -> None:
        self.answers.append(text)

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited = (text, kwargs)


class DummyBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int | str, str, dict[str, Any]]] = []
        self.cb_answers: list[tuple[str, str | None]] = []

    async def send_message(self, chat_id: int | str, text: str, **kwargs: Any) -> None:
        self.messages.append((chat_id, text, kwargs))

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None, **kwargs: Any
    ) -> None:
        self.cb_answers.append((callback_query_id, text))


class DummyJob:
    def __init__(
        self,
        callback: Callable[..., Any],
        data: dict[str, Any] | None,
        name: str | None,
        time: Any | None = None,
    ) -> None:
        self.callback: Callable[..., Any] = callback
        self.data: dict[str, Any] | None = data
        self.name: str | None = name
        self.time: Any | None = time
        self.removed: bool = False

    def schedule_removal(self) -> None:
        self.removed = True


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_daily(
        self,
        callback: Callable[..., Any],
        time: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(callback, data, name, time)
        self.jobs.append(job)
        return job

    def run_repeating(
        self,
        callback: Callable[..., Any],
        interval: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(callback, data, name)
        self.jobs.append(job)
        return job

    def run_once(
        self,
        callback: Callable[..., Any],
        when: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(callback, data, name)
        self.jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.jobs if j.name == name]


def make_user(user_id: int) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_update(**kwargs: Any) -> MagicMock:
    update = MagicMock(spec=Update)
    for key, value in kwargs.items():
        setattr(update, key, value)
    return update


def make_context(**kwargs: Any) -> MagicMock:
    context = MagicMock(spec=CallbackContext)
    for key, value in kwargs.items():
        setattr(context, key, value)
    return context


def test_schedule_reminder_replaces_existing_job() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="Europe/Moscow"))
        session.add(
            Reminder(
                id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True
            )
        )
        session.commit()
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue)
        handlers.schedule_reminder(rem, job_queue)
    jobs = list(job_queue.get_jobs_by_name("reminder_1"))
    active_jobs = [j for j in jobs if not j.removed]
    assert len(active_jobs) == 1
    job = active_jobs[0]
    assert job.time is not None
    job_time = cast(datetime, job.time)
    assert job_time.tzinfo is not None
    assert isinstance(job_time.tzinfo, ZoneInfo)
    assert job_time.tzinfo.key == "Europe/Moscow"


def test_schedule_with_next_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2024, 1, 1, 10, 0)

    class DummyDatetime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "DummyDatetime":
            result = now
            if tz is not None:
                result = result.replace(tzinfo=tz)
            return cast("DummyDatetime", result)

    monkeypatch.setattr(handlers, "datetime", DummyDatetime)
    user = DbUser(telegram_id=1, thread_id="t", timezone="Europe/Moscow")
    rem = Reminder(
        telegram_id=1, type="sugar", interval_hours=2, is_enabled=True, user=user
    )
    icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏱"
    assert schedule == "каждые 2 ч (next 12:00)"


def test_schedule_with_next_invalid_timezone_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = DbUser(telegram_id=1, thread_id="t", timezone="Invalid/Zone")
    rem = Reminder(
        telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True, user=user
    )
    with caplog.at_level(logging.WARNING):
        icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏰"
    assert any("Invalid timezone" in r.message for r in caplog.records)


def test_schedule_reminder_invalid_timezone_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = DbUser(telegram_id=1, thread_id="t", timezone="Bad/Zone")
    rem = Reminder(
        id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True, user=user
    )
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with caplog.at_level(logging.WARNING):
        handlers.schedule_reminder(rem, job_queue)
    dummy_queue = cast(DummyJobQueue, job_queue)
    assert dummy_queue.jobs
    job = dummy_queue.jobs[0]
    assert job.time is not None
    job_time = cast(datetime, job.time)
    assert job_time.tzinfo is not None
    assert job_time.tzinfo == timezone.utc
    assert any("Invalid timezone" in r.message for r in caplog.records)


def test_render_reminders_formatting(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(handlers, "_limit_for", lambda u: 1)
    # Make _describe deterministic and include status icon to test strikethrough
    monkeypatch.setattr(
        handlers,
        "_describe",
        lambda r, u=None: f"{'🔔' if r.is_enabled else '🔕'}title{r.id}",
    )
    monkeypatch.setattr(settings, "webapp_url", "https://example.org")
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add_all(
            [
                Reminder(
                    id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True
                ),
                Reminder(
                    id=2,
                    telegram_id=1,
                    type="sugar",
                    interval_hours=3,
                    is_enabled=False,
                ),
                Reminder(
                    id=3,
                    telegram_id=1,
                    type="xe_after",
                    minutes_after=15,
                    is_enabled=True,
                ),
            ]
        )
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert markup is not None
    header, *rest = text.splitlines()
    assert header == "Ваши напоминания  (2 / 1 🔔) ⚠️"
    assert "⏰ По времени" in text
    assert "⏱ Интервал" in text
    assert "📸 Триггер-фото" in text
    assert "2. <s>🔕title2</s>" in text
    assert markup.inline_keyboard
    btn = markup.inline_keyboard[-1][0]
    assert btn.web_app and btn.web_app.url.endswith("/ui/reminders")


def test_render_reminders_no_webapp(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(settings, "webapp_url", None)
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True
            )
        )
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert markup is not None
    assert "Нажмите кнопку" not in text
    assert len(markup.inline_keyboard) == 1
    first_row = markup.inline_keyboard[0]
    texts = [btn.text for btn in first_row]
    assert texts == ["🗑️", "🔔"]
    assert all(btn.web_app is None for btn in first_row)


def test_render_reminders_no_entries_no_webapp(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(settings, "webapp_url", None)
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert "У вас нет напоминаний" in text
    assert markup is None


@pytest.mark.asyncio
async def test_reminders_list_no_keyboard(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(settings, "webapp_url", None)
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()

    captured: dict[str, Any] = {}

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        captured["text"] = text
        captured["kwargs"] = kwargs

    message = MagicMock(spec=Message)
    message.reply_text = fake_reply_text
    update = make_update(effective_user=make_user(1), message=message)
    context = make_context()
    await handlers.reminders_list(update, context)
    text = captured.get("text")
    assert text is not None
    assert "У вас нет напоминаний" in text
    kwargs = captured.get("kwargs")
    assert kwargs is not None
    assert "reply_markup" not in kwargs


@pytest.mark.asyncio
async def test_toggle_reminder_cb(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True
            )
        )
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue)

    query = DummyCallbackQuery("rem_toggle:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        make_context(job_queue=job_queue, user_data={"pending_entry": {}}),
    )
    await handlers.reminder_action_cb(update, context)
    await router.callback_router(update, context)

    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
        assert rem_db is not None
        assert not rem_db.is_enabled
    jobs = list(job_queue.get_jobs_by_name("reminder_1"))
    assert jobs
    job = jobs[0]
    assert job.removed
    assert query.answers
    answer = query.answers[0]
    assert answer == "Готово ✅"
    assert context.user_data is not None
    user_data = context.user_data
    assert "pending_entry" in user_data


@pytest.mark.asyncio
async def test_delete_reminder_cb(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue)

    query = DummyCallbackQuery("rem_del:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=job_queue, user_data={})
    await handlers.reminder_action_cb(update, context)

    with TestSession() as session:
        assert session.query(Reminder).count() == 0
    jobs = list(job_queue.get_jobs_by_name("reminder_1"))
    assert jobs
    job = jobs[0]
    assert job.removed
    assert query.answers
    answer = query.answers[-1]
    assert answer == "Готово ✅"


@pytest.mark.asyncio
async def test_edit_reminder(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="medicine", time=time(8, 0)))
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue)

    msg = DummyMessage()
    web_app_data = MagicMock()
    web_app_data.data = json.dumps({"id": 1, "type": "medicine", "value": "09:00"})
    msg.web_app_data = web_app_data
    update = make_update(effective_message=msg, effective_user=make_user(1))
    context = make_context(job_queue=job_queue)
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        parsed = parse_time_interval("09:00")
        assert isinstance(parsed, time)
        rem_db = session.get(Reminder, 1)
        assert rem_db is not None
        assert rem_db.time == parsed
    jobs = list(job_queue.get_jobs_by_name("reminder_1"))
    assert len(jobs) == 2
    assert jobs[0].removed is True
    assert jobs[1].removed is False


@pytest.mark.asyncio
async def test_trigger_job_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(23, 0)))
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
        assert rem_db is not None
        rem = Reminder(
            id=rem_db.id,
            telegram_id=rem_db.telegram_id,
            type=rem_db.type,
            time=rem_db.time,
        )
    handlers.schedule_reminder(rem, job_queue)
    bot = DummyBot()
    job = MagicMock(spec=Job)
    job.data = {"reminder_id": 1, "chat_id": 1}
    context = make_context(bot=bot, job=job, job_queue=job_queue)
    await handlers.reminder_job(context)
    assert bot.messages
    _, text_msg, kwargs = bot.messages[0]
    assert kwargs is not None
    assert text_msg.startswith("🔔 Замерить сахар")
    reply_markup = kwargs.get("reply_markup")
    assert reply_markup is not None
    assert reply_markup.inline_keyboard
    keyboard = reply_markup.inline_keyboard[0]
    assert len(keyboard) >= 2
    assert keyboard[0].callback_data == "remind_snooze:1"
    assert keyboard[1].callback_data == "remind_cancel:1"
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "trigger"


@pytest.mark.asyncio
async def test_cancel_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyCallbackQuery("remind_cancel:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=DummyJobQueue(), bot=DummyBot())
    await handlers.reminder_callback(update, context)
    assert query.edited is not None
    edited_text, _ = query.edited
    assert edited_text == "❌ Напоминание отменено"
    assert query.answers == [None]
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "remind_cancel"


@pytest.mark.asyncio
async def test_reminder_callback_foreign_rid(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyCallbackQuery("remind_cancel:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(2))
    context = make_context(job_queue=DummyJobQueue(), bot=DummyBot())
    await handlers.reminder_callback(update, context)

    assert query.answers == ["Не найдено"]
    assert query.edited is None
    with TestSession() as session:
        assert session.query(ReminderLog).count() == 0


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.fixture()
def client(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    app = FastAPI()
    app.include_router(reminders_router, prefix="/api")
    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
    with TestClient(app) as test_client:
        yield test_client


def test_empty_returns_200(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == []


def test_nonempty_returns_list(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                title="Sugar check",
                time=time(8, 0),
                interval_hours=3,
            )
        )
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "telegramId": 1,
            "id": 1,
            "type": "sugar",
            "title": "Sugar check",
            "time": "08:00",
            "intervalHours": 3,
            "minutesAfter": None,
            "isEnabled": True,
            "orgId": None,
        }
    ]


def test_get_single_reminder(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                title="Sugar check",
                time=time(8, 0),
                interval_hours=3,
            )
        )
        session.commit()
    resp = client.get("/api/reminders/1", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == {
        "telegramId": 1,
        "id": 1,
        "type": "sugar",
        "title": "Sugar check",
        "time": "08:00",
        "intervalHours": 3,
        "minutesAfter": None,
        "isEnabled": True,
        "orgId": None,
    }


def test_real_404(client: TestClient) -> None:
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.get("/api/reminders", params={"telegramId": 2})
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_single_reminder_not_found(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.get("/api/reminders/1", params={"telegramId": 1})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "reminder not found"}


def test_post_reminder_forbidden(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"detail": "forbidden"}
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 1}


def test_patch_reminder_forbidden(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                is_enabled=True,
            )
        )
        session.commit()
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.patch(
        "/api/reminders",
        json={"telegramId": 1, "id": 1, "type": "sugar"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"detail": "forbidden"}
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
