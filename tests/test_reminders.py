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

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)


class DummyCallbackQuery:
    def __init__(self, data, message):
        self.data = data
        self.message = message

    async def answer(self):
        pass


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


@pytest.mark.asyncio
async def test_add_reminder_conversation_success(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    job_queue = DummyJobQueue()
    context = SimpleNamespace(user_data={}, job_queue=job_queue)

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_start(update, context)
    assert state == handlers.REMINDER_TYPE

    msg2 = DummyMessage()
    cq = DummyCallbackQuery("rem_type:sugar", msg2)
    update2 = SimpleNamespace(callback_query=cq, effective_user=SimpleNamespace(id=1))
    state2 = await handlers.add_reminder_type(update2, context)
    assert state2 == handlers.REMINDER_VALUE

    msg3 = DummyMessage(text="23:00")
    update3 = SimpleNamespace(message=msg3, effective_user=SimpleNamespace(id=1))
    state3 = await handlers.add_reminder_value(update3, context)
    assert state3 == handlers.ConversationHandler.END

    with TestSession() as session:
        rem = session.query(Reminder).first()
        rid = rem.id

    msg_del = DummyMessage()
    update_del = SimpleNamespace(message=msg_del, effective_user=SimpleNamespace(id=1))
    context_del = SimpleNamespace(args=[str(rid)], job_queue=job_queue)
    await handlers.delete_reminder(update_del, context_del)
    with TestSession() as session:
        assert session.query(Reminder).count() == 0


@pytest.mark.asyncio
async def test_add_multiple_reminders_sequential(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    job_queue = DummyJobQueue()
    context = SimpleNamespace(user_data={}, job_queue=job_queue)

    # First reminder
    msg1 = DummyMessage()
    update1 = SimpleNamespace(message=msg1, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_start(update1, context)
    assert state == handlers.REMINDER_TYPE

    cq1 = DummyCallbackQuery("rem_type:sugar", DummyMessage())
    update2 = SimpleNamespace(callback_query=cq1, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_type(update2, context)
    assert state == handlers.REMINDER_VALUE

    msg_val1 = DummyMessage(text="08:00")
    update3 = SimpleNamespace(message=msg_val1, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_value(update3, context)
    assert state == handlers.ConversationHandler.END
    assert "добавить ещё" in msg_val1.texts[0].lower()

    # Second reminder
    msg4 = DummyMessage()
    update4 = SimpleNamespace(message=msg4, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_start(update4, context)
    assert state == handlers.REMINDER_TYPE

    cq2 = DummyCallbackQuery("rem_type:medicine", DummyMessage())
    update5 = SimpleNamespace(callback_query=cq2, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_type(update5, context)
    assert state == handlers.REMINDER_VALUE

    msg_val2 = DummyMessage(text="09:00")
    update6 = SimpleNamespace(message=msg_val2, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_value(update6, context)
    assert state == handlers.ConversationHandler.END
    assert "добавить ещё" in msg_val2.texts[0].lower()

    with TestSession() as session:
        rems = session.query(Reminder).filter_by(telegram_id=1).all()
        assert len(rems) == 2


@pytest.mark.asyncio
async def test_add_reminder_invalid_input(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    job_queue = DummyJobQueue()
    context = SimpleNamespace(user_data={}, job_queue=job_queue)

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    await handlers.add_reminder_start(update, context)

    cq = DummyCallbackQuery("rem_type:sugar", DummyMessage())
    update2 = SimpleNamespace(callback_query=cq, effective_user=SimpleNamespace(id=1))
    await handlers.add_reminder_type(update2, context)

    msg_bad = DummyMessage(text="abc")
    update_bad = SimpleNamespace(message=msg_bad, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_value(update_bad, context)
    assert state == handlers.REMINDER_VALUE
    assert msg_bad.texts == ["Интервал должен быть числом."]
    with TestSession() as session:
        assert session.query(Reminder).count() == 0


@pytest.mark.asyncio
async def test_add_reminder_cancel(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    job_queue = DummyJobQueue()
    context = SimpleNamespace(user_data={}, job_queue=job_queue)

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_start(update, context)
    assert state == handlers.REMINDER_TYPE

    cancel_msg = DummyMessage()
    cancel_update = SimpleNamespace(message=cancel_msg, effective_user=SimpleNamespace(id=1))
    end_state = await handlers.add_reminder_cancel(cancel_update, context)
    assert end_state == handlers.ConversationHandler.END
    with TestSession() as session:
        assert session.query(Reminder).count() == 0

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
    assert bot.messages[0][1].startswith("Замерить сахар")
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log.action == "trigger"
