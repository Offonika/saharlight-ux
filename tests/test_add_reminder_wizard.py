import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Reminder
import diabetes.reminder_handlers as handlers
from diabetes.common_handlers import commit_session


class DummyMessage:
    def __init__(self, text: str | None = None):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class DummyCallbackQuery:
    def __init__(self, data, message, id="1"):
        self.data = data
        self.message = message
        self.id = id
        self.answers: list[str | None] = []

    async def answer(self, text: str | None = None, **kwargs):
        self.answers.append(text)


class DummyBot:
    def __init__(self):
        self.cb_answers: list[tuple[str, str | None]] = []

    async def answer_callback_query(self, callback_query_id, text: str | None = None, **kwargs):
        self.cb_answers.append((callback_query_id, text))


class DummyJobQueue:
    def __init__(self):
        self.jobs = []

    def run_daily(self, callback, time, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def run_repeating(self, callback, interval, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def get_jobs_by_name(self, name):
        return [j for j in self.jobs if j.name == name]


class DummyJob:
    def __init__(self, callback, data, name):
        self.callback = callback
        self.data = data
        self.name = name
        self.removed = False

    def schedule_removal(self):
        self.removed = True


@pytest.mark.asyncio
async def test_add_reminder_wizard_success(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    job_queue = DummyJobQueue()
    bot = DummyBot()
    context = SimpleNamespace(user_data={}, job_queue=job_queue, bot=bot)

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_start(update, context)
    assert state == handlers.REMINDER_TYPE

    cq = DummyCallbackQuery("rem_type:sugar", DummyMessage(), id="cb1")
    update2 = SimpleNamespace(callback_query=cq, effective_user=SimpleNamespace(id=1))
    monkeypatch.setattr(handlers, "_schedule_with_next", lambda rem: ("⏰", "next 23:00"))
    state = await handlers.add_reminder_type(update2, context)
    assert state == handlers.REMINDER_TIME

    msg_time = DummyMessage(text="23:00")
    update3 = SimpleNamespace(message=msg_time, effective_user=SimpleNamespace(id=1))
    end_state = await handlers.add_reminder_time(update3, context)
    assert end_state == handlers.ConversationHandler.END

    assert bot.cb_answers[0] == ("cb1", "Напоминание добавлено (next 23:00)")
    with TestSession() as session:
        assert session.query(Reminder).count() == 1


@pytest.mark.asyncio
async def test_add_reminder_wizard_cancel(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    bot = DummyBot()
    context = SimpleNamespace(user_data={}, bot=bot)

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_start(update, context)
    assert state == handlers.REMINDER_TYPE

    cq = DummyCallbackQuery("cancel", DummyMessage(), id="cb2")
    update2 = SimpleNamespace(callback_query=cq, effective_user=SimpleNamespace(id=1))
    end_state = await handlers.add_reminder_cancel(update2, context)
    assert end_state == handlers.ConversationHandler.END
    assert cq.answers[-1] == "Отменено"
