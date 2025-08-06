import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Reminder, ReminderLog
import diabetes.reminder_handlers as handlers
from diabetes.common_handlers import commit_session


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
    def __init__(self, data, message):
        self.data = data
        self.message = message
        self.answers = []
        self.edited = None

    async def answer(self, text=None, **kwargs):
        self.answers.append(text)

    async def edit_message_text(self, text, **kwargs):
        self.edited = (text, kwargs)


class DummyBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))


class DummyJob:
    def __init__(self, callback, data, name):
        self.callback = callback
        self.data = data
        self.name = name
        self.removed = False

    def schedule_removal(self):
        self.removed = True


class DummyJobQueue:
    def __init__(self):
        self.jobs = []

    def run_daily(self, callback, time, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def run_repeating(self, callback, interval, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def run_once(self, callback, when, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def get_jobs_by_name(self, name):
        return [j for j in self.jobs if j.name == name]


def test_render_reminders_formatting(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(handlers, "_limit_for", lambda u: 1)
    monkeypatch.setattr(handlers, "_describe", lambda r: f"title{r.id}")
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
    text, markup = handlers._render_reminders(1)
    header, *rest = text.splitlines()
    assert header == "Ваши напоминания  (2 / 1 🔔) ⚠️"
    assert "⏰ По времени" in text
    assert "⏱ Интервал" in text
    assert "📸 Триггер-фото" in text
    assert "2. <s>title2</s>" in text
    assert markup.inline_keyboard[-1][0].callback_data == "add_new"


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

    query = DummyCallbackQuery("toggle:1", DummyMessage())
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=job_queue, user_data={})
    await handlers.reminder_action_cb(update, context)

    with TestSession() as session:
        assert not session.get(Reminder, 1).is_enabled
    assert job_queue.get_jobs_by_name("reminder_1")[0].removed
    assert query.answers[-1] == "Готово ✅"


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

    query = DummyCallbackQuery("del:1", DummyMessage())
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

    query = DummyCallbackQuery("edit:1", DummyMessage())
    context = SimpleNamespace(user_data={}, job_queue=job_queue)
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    await handlers.reminder_action_cb(update, context)
    assert query.answers[-1] == "Готово ✅"

    msg = DummyMessage(text="09:00")
    update2 = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    await handlers.reminder_edit_reply(update2, context)

    with TestSession() as session:
        assert session.get(Reminder, 1).time == "09:00"
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
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log.action == "trigger"
