import pytest

import diabetes.reminder_handlers as handlers
from diabetes.common_handlers import commit_session
from diabetes.db import Base, User, Reminder, Entry

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from types import SimpleNamespace


class DummyMessage:
    def __init__(self, text: str | None = None):
        self.text = text
        self.replies: list[str] = []
        self.edited = None

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)

    async def edit_text(self, text, **kwargs):
        self.edited = (text, kwargs)


class DummyCallbackQuery:
    def __init__(self, data: str, message: DummyMessage, id: str = "1"):
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
    def get_jobs_by_name(self, name):
        return []

    def run_daily(self, *args, **kwargs):
        pass

    def run_repeating(self, *args, **kwargs):
        pass


def _setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time="08:00",
                is_enabled=True,
            )
        )
        session.commit()
    return TestSession


@pytest.mark.asyncio
async def test_bad_input_does_not_create_entry():
    TestSession = _setup_db()
    context = SimpleNamespace(user_data={}, job_queue=DummyJobQueue(), bot=DummyBot())
    cq = DummyCallbackQuery("rem_edit:1", DummyMessage())
    update = SimpleNamespace(callback_query=cq, effective_user=SimpleNamespace(id=1))
    state = await handlers.reminder_action_cb(update, context)
    assert state == handlers.REM_EDIT_AWAIT_INPUT

    msg = DummyMessage(text="5")
    update2 = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    state = await handlers.reminder_edit_reply(update2, context)
    assert state == handlers.REM_EDIT_AWAIT_INPUT
    assert msg.replies and "Неверный формат" in msg.replies[0]
    with TestSession() as session:
        assert session.query(Entry).count() == 0


@pytest.mark.asyncio
async def test_good_input_updates_and_ends():
    TestSession = _setup_db()
    context = SimpleNamespace(user_data={}, job_queue=DummyJobQueue(), bot=DummyBot())
    msg_initial = DummyMessage()
    cq = DummyCallbackQuery("rem_edit:1", msg_initial, id="cb1")
    update = SimpleNamespace(callback_query=cq, effective_user=SimpleNamespace(id=1))
    state = await handlers.reminder_action_cb(update, context)
    assert state == handlers.REM_EDIT_AWAIT_INPUT

    msg = DummyMessage(text="09:30")
    update2 = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    end_state = await handlers.reminder_edit_reply(update2, context)
    assert end_state == handlers.ConversationHandler.END
    assert msg.replies and msg.replies[-1] == "Готово ✅"
    assert msg_initial.edited is not None
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem.time == "09:30"
        assert rem.interval_hours is None
        assert session.query(Entry).count() == 0
    assert "edit_reminder_id" not in context.user_data

