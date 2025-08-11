import json
import pytest
from datetime import datetime
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Reminder, ReminderLog
import diabetes.reminder_handlers as handlers
import diabetes.common_handlers as common_handlers
from diabetes.common_handlers import commit_session
from diabetes.utils import parse_time_interval


class DummyMessage:
    def __init__(self, text=None):
        self.text = text
        self.texts = []
        self.edited = None

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)

    async def edit_text(self, text, **kwargs):
        self.edited = (text, kwargs)


class DummyCallbackQuery:
    def __init__(self, data, message, id="1"):
        self.data = data
        self.message = message
        self.id = id
        self.answers = []
        self.edited = None

    async def answer(self, text=None, **kwargs):
        self.answers.append(text)

    async def edit_message_text(self, text, **kwargs):
        self.edited = (text, kwargs)


class DummyBot:
    def __init__(self):
        self.messages = []
        self.cb_answers = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))

    async def answer_callback_query(self, callback_query_id, text: str | None = None, **kwargs):
        self.cb_answers.append((callback_query_id, text))


class DummyJob:
    def __init__(self, callback, data, name, time=None):
        self.callback = callback
        self.data = data
        self.name = name
        self.time = time
        self.removed = False

    def schedule_removal(self):
        self.removed = True


class DummyJobQueue:
    def __init__(self):
        self.jobs = []

    def run_daily(self, callback, time, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name, time))

    def run_repeating(self, callback, interval, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def run_once(self, callback, when, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def get_jobs_by_name(self, name):
        return [j for j in self.jobs if j.name == name]


def test_schedule_reminder_replaces_existing_job():
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


def test_schedule_with_next_interval(monkeypatch):
    now = datetime(2024, 1, 1, 10, 0)

    class DummyDatetime(datetime):
        @classmethod
        def now(cls):  # type: ignore[override]
            return now

    monkeypatch.setattr(handlers, "datetime", DummyDatetime)
    user = User(telegram_id=1, thread_id="t", timezone="Europe/Moscow")
    rem = Reminder(telegram_id=1, type="sugar", interval_hours=2, is_enabled=True, user=user)
    icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏱"
    assert schedule == "каждые 2 ч (next 12:00)"


def test_render_reminders_formatting(monkeypatch):
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
    monkeypatch.setattr(handlers, "WEBAPP_URL", "https://example.org")
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


def test_render_reminders_no_webapp(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(handlers, "WEBAPP_URL", None)
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


@pytest.mark.asyncio
async def test_toggle_reminder_cb(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        handlers.schedule_reminder(rem, job_queue)

    query = DummyCallbackQuery("rem_toggle:1", DummyMessage())
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=job_queue, user_data={"pending_entry": {}})
    await handlers.reminder_action_cb(update, context)
    await common_handlers.callback_router(update, context)

    with TestSession() as session:
        assert not session.get(Reminder, 1).is_enabled
    assert job_queue.get_jobs_by_name("reminder_1")[0].removed
    assert query.answers[0] == "Готово ✅"
    assert "pending_entry" in context.user_data


@pytest.mark.asyncio
async def test_delete_reminder_cb(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00"))
        session.commit()

    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        handlers.schedule_reminder(rem, job_queue)

    query = DummyCallbackQuery("rem_del:1", DummyMessage())
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=job_queue, user_data={})
    await handlers.reminder_action_cb(update, context)

    with TestSession() as session:
        assert session.query(Reminder).count() == 0
    assert job_queue.get_jobs_by_name("reminder_1")[0].removed
    assert query.answers[-1] == "Готово ✅"


@pytest.mark.asyncio
async def test_edit_reminder(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

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
    update = SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=job_queue)
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        parsed = parse_time_interval("09:00")
        assert session.get(Reminder, 1).time == parsed.strftime("%H:%M")
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert len(jobs) == 2
    assert jobs[0].removed is True
    assert jobs[1].removed is False

@pytest.mark.asyncio
async def test_trigger_job_logs(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

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
    context = SimpleNamespace(
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
async def test_cancel_callback(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00"))
        session.commit()

    query = DummyCallbackQuery("remind_cancel:1", DummyMessage())
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=DummyJobQueue(), bot=DummyBot())
    await handlers.reminder_callback(update, context)

    assert query.edited[0] == "❌ Напоминание отменено"
    assert query.answers == [None]
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log.action == "remind_cancel"
