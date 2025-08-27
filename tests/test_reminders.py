import json
import logging
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from typing import Any

from services.api.app.diabetes.services.db import Base, User, Reminder, ReminderLog
import services.api.app.diabetes.handlers.reminder_handlers as handlers
import services.api.app.diabetes.handlers.router as router
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.helpers import parse_time_interval
from services.api.app.config import settings
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.edited: tuple[str, dict[str, Any]] | None = None

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)

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
    def __init__(self, callback: Any, data: Any, name: Any, time: Any=None) -> None:
        self.callback = callback
        self.data = data
        self.name = name
        self.time = time
        self.removed = False

    def schedule_removal(self) -> None:
        self.removed = True


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs = []

    def run_daily(self, callback: Any, time: Any, data: Any=None, name: Any=None) -> None:
        self.jobs.append(DummyJob(callback, data, name, time))

    def run_repeating(self, callback: Any, interval: Any, data: Any=None, name: Any=None) -> None:
        self.jobs.append(DummyJob(callback, data, name))

    def run_once(self, callback: Any, when: Any, data: Any=None, name: Any=None) -> None:
        self.jobs.append(DummyJob(callback, data, name))

    def get_jobs_by_name(self, name: Any) -> None:
        return [j for j in self.jobs if j.name == name]


def test_schedule_reminder_replaces_existing_job() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="Europe/Moscow"))
        session.add(
            Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True)
        )
        session.commit()
    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        handlers.schedule_reminder(rem, job_queue)
        handlers.schedule_reminder(rem, job_queue)
    jobs = job_queue.get_jobs_by_name("reminder_1")
    active_jobs = [j for j in jobs if not j.removed]
    assert len(active_jobs) == 1
    assert active_jobs[0].time.tzinfo.key == "Europe/Moscow"


def test_schedule_with_next_interval(monkeypatch: Any) -> None:
    now = datetime(2024, 1, 1, 10, 0)

    class DummyDatetime(datetime):
        @classmethod
        def now(cls) -> None:  # type: ignore[override]
            return now

    monkeypatch.setattr(handlers, "datetime", DummyDatetime)
    user = User(telegram_id=1, thread_id="t", timezone="Europe/Moscow")
    rem = Reminder(telegram_id=1, type="sugar", interval_hours=2, is_enabled=True, user=user)
    icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏱"
    assert schedule == "каждые 2 ч (next 12:00)"


def test_schedule_with_next_invalid_timezone_logs_warning(caplog: Any) -> None:
    user = User(telegram_id=1, thread_id="t", timezone="Invalid/Zone")
    rem = Reminder(telegram_id=1, type="sugar", time="08:00", is_enabled=True, user=user)
    with caplog.at_level(logging.WARNING):
        icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏰"
    assert any("Invalid timezone" in r.message for r in caplog.records)


def test_schedule_reminder_invalid_timezone_logs_warning(caplog: Any) -> None:
    user = User(telegram_id=1, thread_id="t", timezone="Bad/Zone")
    rem = Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True, user=user)
    job_queue = DummyJobQueue()
    with caplog.at_level(logging.WARNING):
        handlers.schedule_reminder(rem, job_queue)
    assert job_queue.jobs
    assert job_queue.jobs[0].time.tzinfo == timezone.utc
    assert any("Invalid timezone" in r.message for r in caplog.records)


def test_render_reminders_formatting(monkeypatch: Any) -> None:
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
        session.add(User(telegram_id=1, thread_id="t"))
        session.add_all(
            [
                Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True),
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
    header, *rest = text.splitlines()
    assert header == "Ваши напоминания  (2 / 1 🔔) ⚠️"
    assert "⏰ По времени" in text
    assert "⏱ Интервал" in text
    assert "📸 Триггер-фото" in text
    assert "2. <s>🔕title2</s>" in text
    btn = markup.inline_keyboard[-1][0]
    assert btn.web_app and btn.web_app.url.endswith("/reminders")


def test_render_reminders_no_webapp(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(settings, "webapp_url", None)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True))
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert "Нажмите кнопку" not in text
    assert len(markup.inline_keyboard) == 1
    texts = [btn.text for btn in markup.inline_keyboard[0]]
    assert texts == ["🗑️", "🔔"]
    assert all(btn.web_app is None for btn in markup.inline_keyboard[0])


def test_render_reminders_no_entries_no_webapp(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(settings, "webapp_url", None)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert "У вас нет напоминаний" in text
    assert markup is None


@pytest.mark.asyncio
async def test_reminders_list_no_keyboard(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(settings, "webapp_url", None)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    captured: dict[str, dict] = {}

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        captured["text"] = text
        captured["kwargs"] = kwargs

    update = make_update(
        effective_user=SimpleNamespace(id=1),
        message=SimpleNamespace(reply_text=fake_reply_text),
    )
    context = make_context()
    await handlers.reminders_list(update, context)
    assert "У вас нет напоминаний" in captured["text"]
    assert "reply_markup" not in captured["kwargs"]


@pytest.mark.asyncio
async def test_toggle_reminder_cb(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        handlers.schedule_reminder(rem, job_queue)

    query = DummyCallbackQuery("rem_toggle:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = make_context(job_queue=job_queue, user_data={"pending_entry": {}})
    await handlers.reminder_action_cb(update, context)
    await router.handle_unknown_callback(update, context)

    with TestSession() as session:
        assert not session.get(Reminder, 1).is_enabled
    assert job_queue.get_jobs_by_name("reminder_1")[0].removed
    assert query.answers[0] == "Готово ✅"
    assert "pending_entry" in context.user_data


@pytest.mark.asyncio
async def test_delete_reminder_cb(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00"))
        session.commit()

    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        handlers.schedule_reminder(rem, job_queue)

    query = DummyCallbackQuery("rem_del:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = make_context(job_queue=job_queue, user_data={})
    await handlers.reminder_action_cb(update, context)

    with TestSession() as session:
        assert session.query(Reminder).count() == 0
    assert job_queue.get_jobs_by_name("reminder_1")[0].removed
    assert query.answers[-1] == "Готово ✅"


@pytest.mark.asyncio
async def test_edit_reminder(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="medicine", time="08:00"))
        session.commit()

    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        handlers.schedule_reminder(rem, job_queue)

    msg = DummyMessage()
    msg.web_app_data = SimpleNamespace(
        data=json.dumps({"id": 1, "type": "medicine", "value": "09:00"})
    )
    update = make_update(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = make_context(job_queue=job_queue)
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        parsed = parse_time_interval("09:00")
        assert session.get(Reminder, 1).time == parsed.strftime("%H:%M")
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert len(jobs) == 2
    assert jobs[0].removed is True
    assert jobs[1].removed is False

@pytest.mark.asyncio
async def test_trigger_job_logs(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="23:00"))
        session.commit()

    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
        rem = Reminder(
            id=rem_db.id,
            telegram_id=rem_db.telegram_id,
            type=rem_db.type,
            time=rem_db.time,
        )
    handlers.schedule_reminder(rem, job_queue)
    bot = DummyBot()
    context = make_context(
        bot=bot,
        job=SimpleNamespace(data={"reminder_id": 1, "chat_id": 1}),
        job_queue=job_queue,
    )
    await handlers.reminder_job(context)
    assert bot.messages[0][1].startswith("🔔 Замерить сахар")
    keyboard = bot.messages[0][2]["reply_markup"].inline_keyboard[0]
    assert keyboard[0].callback_data == "remind_snooze:1"
    assert keyboard[1].callback_data == "remind_cancel:1"
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log.action == "trigger"


@pytest.mark.asyncio
async def test_cancel_callback(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00"))
        session.commit()

    query = DummyCallbackQuery("remind_cancel:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = make_context(job_queue=DummyJobQueue(), bot=DummyBot())
    await handlers.reminder_callback(update, context)

    assert query.edited[0] == "❌ Напоминание отменено"
    assert query.answers == [None]
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log.action == "remind_cancel"


@pytest.mark.asyncio
async def test_reminder_callback_foreign_rid(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00"))
        session.commit()

    query = DummyCallbackQuery("remind_cancel:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=SimpleNamespace(id=2))
    context = make_context(job_queue=DummyJobQueue(), bot=DummyBot())
    await handlers.reminder_callback(update, context)

    assert query.answers == ["Не найдено"]
    assert query.edited is None
    with TestSession() as session:
        assert session.query(ReminderLog).count() == 0

