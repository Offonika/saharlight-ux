import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Profile, Alert, Reminder
import diabetes.profile_handlers as handlers
from diabetes.common_handlers import commit_session
import diabetes.reminder_handlers as reminder_handlers


class DummyMessage:
    def __init__(self):
        self.texts = []
        self.markups = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))


class DummyQuery:
    def __init__(self, data):
        self.data = data
        self.edits = []
        self.message = DummyMessage()

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


@pytest.mark.asyncio
async def test_profile_view_has_security_button(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, icr=10, cf=2, target_bg=6))
        session.commit()

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace()

    await handlers.profile_view(update, context)

    markup = msg.markups[0]
    buttons = [b for row in markup.inline_keyboard for b in row]
    callbacks = {b.text: b.callback_data for b in buttons}
    assert callbacks["🔔 Безопасность"] == "profile_security"


@pytest.mark.parametrize(
    "action, expected_low, expected_high",
    [
        ("low_inc", 4.5, 9.0),
        ("low_dec", 3.5, 9.0),
        ("high_inc", 4.0, 9.5),
        ("high_dec", 4.0, 8.5),
    ],
)
@pytest.mark.asyncio
async def test_profile_security_threshold_changes(monkeypatch, action, expected_low, expected_high):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit_session", commit_session)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=9,
                sos_alerts_enabled=True,
            )
        )
        session.add(Alert(user_id=1, sugar=5))
        session.commit()

    calls = []

    def fake_eval(user_id, sugar, job_queue):
        calls.append((user_id, sugar, job_queue))

    monkeypatch.setattr(handlers, "evaluate_sugar", fake_eval)

    query = DummyQuery(f"profile_security:{action}")
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(application=SimpleNamespace(job_queue="jq"))

    await handlers.profile_security(update, context)

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile.low_threshold == expected_low
        assert profile.high_threshold == expected_high

    assert calls == [(1, 5, "jq")]


@pytest.mark.asyncio
async def test_profile_security_toggle_sos_alerts(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit_session", commit_session)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=9,
                sos_alerts_enabled=False,
            )
        )
        session.add(Alert(user_id=1, sugar=7))
        session.commit()

    calls = []

    def fake_eval(user_id, sugar, job_queue):
        calls.append((user_id, sugar, job_queue))

    monkeypatch.setattr(handlers, "evaluate_sugar", fake_eval)

    query = DummyQuery("profile_security:toggle_sos")
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(application=SimpleNamespace(job_queue="jq"))

    await handlers.profile_security(update, context)

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile.sos_alerts_enabled is True

    assert calls == [(1, 7, "jq")]


@pytest.mark.asyncio
async def test_profile_security_shows_reminders(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit_session", commit_session)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                icr=10,
                cf=2,
                target_bg=6,
                low_threshold=4,
                high_threshold=9,
                sos_alerts_enabled=True,
            )
        )
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00"))
        session.commit()

    query = DummyQuery("profile_security")
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(application=SimpleNamespace(job_queue="jq"))

    await handlers.profile_security(update, context)

    text, _ = query.edits[0]
    assert "1. Замерить сахар 08:00" in text


@pytest.mark.asyncio
async def test_profile_security_add_delete_calls_handlers(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "commit_session", commit_session)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, icr=10, cf=2, target_bg=6))
        session.commit()

    called = {"add": False, "del": False}

    async def fake_add(update, context):
        called["add"] = True

    async def fake_del(update, context):
        called["del"] = True

    monkeypatch.setattr(reminder_handlers, "add_reminder", fake_add)
    monkeypatch.setattr(reminder_handlers, "delete_reminder", fake_del)

    query_add = DummyQuery("profile_security:add")
    update_add = SimpleNamespace(callback_query=query_add, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(application=SimpleNamespace(job_queue="jq"))

    await handlers.profile_security(update_add, context)
    assert called["add"] is True

    query_del = DummyQuery("profile_security:del")
    update_del = SimpleNamespace(callback_query=query_del, effective_user=SimpleNamespace(id=1))

    await handlers.profile_security(update_del, context)
    assert called["del"] is True
