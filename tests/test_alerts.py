from datetime import timedelta
from types import SimpleNamespace
from typing import Any, Callable, Optional, cast

from telegram.ext import CallbackContext, Job, JobQueue

from .context_stub import AlertContext, ContextStub

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.handlers.alert_handlers as handlers
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.services.db import Base, User, Profile, Alert
from tests.helpers import make_update


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

    def get_jobs_by_name(self, name: str) -> None:
        return [j for j in self.jobs if j.name == name]


@pytest.mark.asyncio
async def test_threshold_evaluation() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t1"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.add(User(telegram_id=2, thread_id="t2"))
        session.add(Profile(telegram_id=2, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue_low = DummyJobQueue()
    await handlers.evaluate_sugar(1, 3, cast(JobQueue[Any], job_queue_low))
    with TestSession() as session:
        alert = session.query(Alert).filter_by(user_id=1).first()
        assert alert is not None
        assert alert.type == "hypo"
    assert job_queue_low.get_jobs_by_name("alert_1")
    assert job_queue_low.jobs[0].when == handlers.ALERT_REPEAT_DELAY

    job_queue_high = DummyJobQueue()
    await handlers.evaluate_sugar(2, 9, cast(JobQueue[Any], job_queue_high))
    with TestSession() as session:
        alert2 = session.query(Alert).filter_by(user_id=2).first()
        assert alert2 is not None
        assert alert2.type == "hyper"
    assert job_queue_high.get_jobs_by_name("alert_2")


@pytest.mark.asyncio
async def test_repeat_logic(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    await handlers.evaluate_sugar(1, 3, cast(JobQueue[Any], job_queue))

    calls: list[tuple[int, float]] = []

    async def dummy_send_alert_message(
        user_id: int,
        sugar: float,
        profile: dict[str, Any],
        context: Any,
        first_name: str,
    ) -> None:
        calls.append((user_id, sugar))

    monkeypatch.setattr(handlers, "_send_alert_message", dummy_send_alert_message)

    for i in range(handlers.MAX_REPEATS):
        job = job_queue.jobs[i]
        context = cast(
            AlertContext,
            ContextStub(
                job=cast(Job[Any], job),
                job_queue=cast(JobQueue[Any], job_queue),
                bot=SimpleNamespace(),
            ),
        )
        await handlers.alert_job(cast(CallbackContext[Any, Any, Any, Any], context))

    assert len(job_queue.jobs) == handlers.MAX_REPEATS
    assert len(calls) == handlers.MAX_REPEATS
    assert job_queue.jobs[-1].removed


@pytest.mark.asyncio
async def test_normal_reading_resolves_alert() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    await handlers.evaluate_sugar(1, 3, cast(JobQueue[Any], job_queue))
    assert job_queue.jobs

    await handlers.evaluate_sugar(1, 5, cast(JobQueue[Any], job_queue))
    with TestSession() as session:
        alert = session.query(Alert).filter_by(user_id=1).first()
        assert alert is not None
        assert alert.resolved
    assert job_queue.jobs[0].removed


@pytest.mark.asyncio
async def test_three_alerts_notify(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

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

    update = make_update(effective_user=SimpleNamespace(id=1, first_name="Ivan"))
    context = cast(AlertContext, ContextStub(bot=DummyBot()))
    async def fake_get_coords_and_link() -> tuple[str, str]:
        return ("0,0", "link")

    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(2):
        await handlers.check_alert(update, cast(CallbackContext[Any, Any, Any, Any], context), 3)
    assert context.bot.sent == []
    await handlers.check_alert(update, cast(CallbackContext[Any, Any, Any, Any], context), 3)
    assert len(context.bot.sent) == 2
    assert context.bot.sent[0][0] == 1
    assert context.bot.sent[1][0] == "@alice"
    with TestSession() as session:
        alerts = session.query(Alert).all()
        assert all(a.resolved for a in alerts)


@pytest.mark.asyncio
async def test_alert_message_without_coords(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

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

    update = make_update(effective_user=SimpleNamespace(id=1, first_name="Ivan"))
    context = cast(AlertContext, ContextStub(bot=DummyBot()))

    async def fake_get_coords_and_link() -> tuple[str | None, str | None]:
        return None, None

    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(3):
        await handlers.check_alert(update, cast(CallbackContext[Any, Any, Any, Any], context), 3)

    msg = "⚠️ У Ivan критический сахар 3 ммоль/л."
    assert context.bot.sent == [(1, msg), ("@alice", msg)]
