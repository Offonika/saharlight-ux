from datetime import timedelta
from types import SimpleNamespace
from typing import Any, Callable, Optional

from typing import cast

from telegram import Bot
from telegram.ext import CallbackContext

from .context_stub import AlertContext, ContextStub

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.handlers.alert_handlers as handlers
from services.api.app.diabetes.handlers.common_handlers import commit_session
from services.api.app.diabetes.services.db import Base, User, Profile, Alert


class DummyJob:
    def __init__(
        self,
        callback: Callable[..., Any],
        when: timedelta,
        data: Optional[dict[str, Any]],
        name: Optional[str],
    ) -> None:
        self.callback: Callable[..., Any] = callback
        self.when: timedelta = when
        self.data: Optional[dict[str, Any]] = data
        self.name: Optional[str] = name
        self.removed: bool = False

    def schedule_removal(self) -> None:
        self.removed = True


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_once(
        self,
        callback: Callable[..., Any],
        when: timedelta,
        data: Optional[dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> None:
        self.jobs.append(DummyJob(callback, when, data, name))

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.jobs if j.name == name]


@pytest.mark.asyncio
async def test_threshold_evaluation() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t1"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.add(User(telegram_id=2, thread_id="t2"))
        session.add(Profile(telegram_id=2, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue_low = DummyJobQueue()
    await handlers.evaluate_sugar(1, 3, job_queue_low)
    with TestSession() as session:
        alert = session.query(Alert).filter_by(user_id=1).first()
        assert alert.type == "hypo"
    assert job_queue_low.get_jobs_by_name("alert_1")
    assert job_queue_low.jobs[0].when == handlers.ALERT_REPEAT_DELAY

    job_queue_high = DummyJobQueue()
    await handlers.evaluate_sugar(2, 9, job_queue_high)
    with TestSession() as session:
        alert2 = session.query(Alert).filter_by(user_id=2).first()
        assert alert2.type == "hyper"
    assert job_queue_high.get_jobs_by_name("alert_2")


@pytest.mark.asyncio
async def test_repeat_logic() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    await handlers.evaluate_sugar(1, 3, job_queue)

    for i in range(1, 4):
        job = SimpleNamespace(data={"user_id": 1, "count": i})
        context: AlertContext = ContextStub(
            job=job, job_queue=job_queue, bot=cast(Bot, SimpleNamespace())
        )
        await handlers.alert_job(cast(CallbackContext, context))

    assert len(job_queue.jobs) == 3


@pytest.mark.asyncio
async def test_normal_reading_resolves_alert() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    await handlers.evaluate_sugar(1, 3, job_queue)
    assert job_queue.jobs

    await handlers.evaluate_sugar(1, 5, job_queue)
    with TestSession() as session:
        alert = session.query(Alert).filter_by(user_id=1).first()
        assert alert.resolved
    assert job_queue.jobs[0].removed


@pytest.mark.asyncio
async def test_three_alerts_notify(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t1"))
        session.add(Profile(
            telegram_id=1,
            low_threshold=4,
            high_threshold=8,
            sos_contact="@alice",
            sos_alerts_enabled=True,
        ))
        session.commit()

    class DummyBot:
        def __init__(self) -> None:
            self.sent: list[tuple[int | str, str]] = []

        async def send_message(self, chat_id: int | str, text: str) -> None:
            self.sent.append((chat_id, text))

    update = SimpleNamespace(effective_user=SimpleNamespace(id=1, first_name="Ivan"))
    context: AlertContext = ContextStub(bot=cast(Bot, DummyBot()))
    async def fake_get_coords_and_link():
        return ("0,0", "link")

    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(2):
        await handlers.check_alert(update, cast(CallbackContext, context), 3)
    assert context.bot.sent == []
    await handlers.check_alert(update, cast(CallbackContext, context), 3)
    assert len(context.bot.sent) == 2
    assert context.bot.sent[0][0] == 1
    assert context.bot.sent[1][0] == "@alice"
    with TestSession() as session:
        alerts = session.query(Alert).all()
        assert all(a.resolved for a in alerts)


@pytest.mark.asyncio
async def test_alert_message_without_coords(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t1"))
        session.add(
            Profile(
                telegram_id=1,
                low_threshold=4,
                high_threshold=8,
                sos_contact="@alice",
                sos_alerts_enabled=True,
            )
        )
        session.commit()

    class DummyBot:
        def __init__(self) -> None:
            self.sent: list[tuple[int | str, str]] = []

        async def send_message(self, chat_id: int | str, text: str) -> None:
            self.sent.append((chat_id, text))

    update = SimpleNamespace(effective_user=SimpleNamespace(id=1, first_name="Ivan"))
    context: AlertContext = ContextStub(bot=cast(Bot, DummyBot()))

    async def fake_get_coords_and_link():
        return None, None

    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(3):
        await handlers.check_alert(update, cast(CallbackContext, context), 3)

    msg = "⚠️ У Ivan критический сахар 3 ммоль/л."
    assert context.bot.sent == [(1, msg), ("@alice", msg)]
