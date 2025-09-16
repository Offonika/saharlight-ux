from __future__ import annotations

import datetime
import logging
from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from telegram.error import TelegramError
from telegram.ext import ContextTypes, JobQueue
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .context_stub import AlertContext, ContextStub
import services.api.app.diabetes.handlers.alert_handlers as handlers
from services.api.app.diabetes.services.db import Alert, Base, Profile, User
from services.api.app.diabetes.services.repository import commit as repo_commit


async def fake_get_coords_and_link() -> tuple[str | None, str | None]:
    """Return empty coordinates for tests."""
    return None, None


class DummyJob:
    """Minimal Job stub for testing schedule_alert."""

    def __init__(
        self,
        *,
        remover: Callable[[DummyJob], None],
        callback: Callable[..., object],
        when: datetime.timedelta,
        data: dict[str, object] | None,
        name: str | None,
    ) -> None:
        self._remover = remover
        self.callback = callback
        self.when = when
        self.data = data
        self.name = name
        self.removed = False

    def remove(self) -> None:
        if self.removed:
            return
        self.removed = True
        self._remover(self)

    def schedule_removal(self) -> None:
        self.remove()


class DummyJobQueue:
    """Collects jobs scheduled via run_once."""

    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_once(
        self,
        callback: Callable[..., object],
        when: datetime.timedelta,
        *,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: object | None = None,
    ) -> None:
        self.jobs.append(
            DummyJob(
                remover=self._remove,
                callback=callback,
                when=when,
                data=data,
                name=name,
            )
        )

    def _remove(self, job: DummyJob) -> None:
        self.jobs = [existing for existing in self.jobs if existing is not job]

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [job for job in self.jobs if job.name == name]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc_cls", "expected"),
    [
        (TelegramError, "Failed to send alert message to user 1"),
        (OSError, "OS error sending alert message to user 1"),
    ],
)
async def test_send_alert_message_invalid_contact(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exc_cls: type[BaseException],
    expected: str,
) -> None:
    """User send failures and invalid SOS contact are logged."""

    bot = SimpleNamespace(send_message=AsyncMock(side_effect=exc_cls("boom")))
    context = cast(AlertContext, ContextStub(bot=bot))
    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    profile: dict[str, Any] = {
        "sos_contact": "bad_contact",
        "sos_alerts_enabled": True,
    }

    with caplog.at_level(logging.INFO):
        await handlers._send_alert_message(
            1,
            10.0,
            profile,
            cast(ContextTypes.DEFAULT_TYPE, context),
            "Ivan",
        )

    assert expected in caplog.text
    assert (
        "SOS contact 'bad_contact' is not a Telegram username, chat id, or phone number; skipping"
        in caplog.text
    )
    assert bot.send_message.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc_cls", "expected"),
    [
        (
            TelegramError,
            "Failed to send alert message to SOS contact '12345'",
        ),
        (
            OSError,
            "OS error sending alert message to SOS contact '12345'",
        ),
    ],
)
async def test_send_alert_message_sos_errors(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exc_cls: type[BaseException],
    expected: str,
) -> None:
    """Failures sending to SOS contact are logged."""

    bot = SimpleNamespace(send_message=AsyncMock(side_effect=[None, exc_cls("boom")]))
    context = cast(AlertContext, ContextStub(bot=bot))
    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    profile: dict[str, Any] = {
        "sos_contact": "12345",
        "sos_alerts_enabled": True,
    }

    with caplog.at_level(logging.ERROR):
        await handlers._send_alert_message(
            1,
            10.0,
            profile,
            cast(ContextTypes.DEFAULT_TYPE, context),
            "Ivan",
        )

    assert expected in caplog.text
    assert bot.send_message.await_count == 2


def test_schedule_alert_schedules_job() -> None:
    """schedule_alert stores a job with expected parameters."""

    job_queue = DummyJobQueue()
    profile: dict[str, object] = {"sos_contact": "@alice"}
    handlers.schedule_alert(
        1,
        cast(JobQueue[Any], job_queue),
        sugar=10.0,
        profile=profile,
        first_name="Ivan",
        count=2,
    )
    assert len(job_queue.jobs) == 1
    job = job_queue.jobs[0]
    assert job.name == "alert_1"
    assert job.when == handlers.ALERT_REPEAT_DELAY
    assert job.data == {
        "user_id": 1,
        "count": 2,
        "sugar": 10.0,
        "profile": profile,
        "first_name": "Ivan",
    }


def test_schedule_alert_replaces_existing_job() -> None:
    """Scheduling twice replaces the previous alert job."""

    job_queue = DummyJobQueue()
    profile: dict[str, object] = {"sos_contact": "@alice"}
    handlers.schedule_alert(
        1,
        cast(JobQueue[Any], job_queue),
        sugar=10.0,
        profile=profile,
        first_name="Ivan",
    )
    first_job = job_queue.jobs[0]

    handlers.schedule_alert(
        1,
        cast(JobQueue[Any], job_queue),
        sugar=11.0,
        profile=profile,
        first_name="Ivan",
        count=2,
    )

    assert len(job_queue.jobs) == 1
    assert job_queue.jobs[0] is not first_job
    assert first_job.removed is True


class DummyJobQueueNoTZ:
    """JobQueue stub without timezone parameter."""

    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_once(
        self,
        callback: Callable[..., object],
        when: datetime.timedelta,
        *,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> None:
        self.jobs.append(
            DummyJob(
                remover=self._remove,
                callback=callback,
                when=when,
                data=data,
                name=name,
            )
        )

    def _remove(self, job: DummyJob) -> None:
        self.jobs = [existing for existing in self.jobs if existing is not job]

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [job for job in self.jobs if job.name == name]


def test_schedule_alert_without_timezone_kwarg() -> None:
    """schedule_alert works when JobQueue.run_once lacks timezone param."""

    job_queue = DummyJobQueueNoTZ()
    profile: dict[str, object] = {"sos_contact": "@alice"}
    handlers.schedule_alert(
        1,
        cast(JobQueue[Any], job_queue),
        sugar=10.0,
        profile=profile,
    )
    assert len(job_queue.jobs) == 1


def _setup_db() -> tuple[Engine, sessionmaker[Session]]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, session_factory


def _prepare_profile(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="thread-1"))
        session.add(
            Profile(
                telegram_id=1,
                low_threshold=4.0,
                high_threshold=8.0,
                sos_contact="@alice",
                sos_alerts_enabled=True,
            )
        )
        session.commit()


def test_db_eval_creates_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    """db_eval creates an alert and requests scheduling."""

    monkeypatch.setattr(handlers, "commit", repo_commit)
    engine, session_factory = _setup_db()
    try:
        _prepare_profile(session_factory)

        with session_factory() as session:
            ok, result = handlers.db_eval(session, 1, 9.5)

        assert ok is True
        assert result is not None
        assert result["action"] == "schedule"
        assert result["notify"] is False
        profile_info = cast(dict[str, object], result["profile"])
        assert profile_info["sos_contact"] == "@alice"
        assert profile_info["sos_alerts_enabled"] is True

        with session_factory() as session:
            alert = session.scalars(sa.select(Alert).filter_by(user_id=1)).one()
            assert alert.type == "hyper"
            assert alert.resolved is False
    finally:
        engine.dispose()


def test_db_eval_resolves_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    """db_eval resolves active alerts when sugar normalises."""

    monkeypatch.setattr(handlers, "commit", repo_commit)
    engine, session_factory = _setup_db()
    try:
        _prepare_profile(session_factory)

        with session_factory() as session:
            ok, _ = handlers.db_eval(session, 1, 3.0)

        assert ok is True

        with session_factory() as session:
            active = session.scalars(sa.select(Alert).filter_by(user_id=1)).one()
            assert active.resolved is False

        with session_factory() as session:
            ok, result = handlers.db_eval(session, 1, 5.0)

        assert ok is True
        assert result is not None
        assert result["action"] == "remove"
        assert result["notify"] is False

        with session_factory() as session:
            resolved = session.scalars(sa.select(Alert).filter_by(user_id=1)).one()
            assert resolved.resolved is True
    finally:
        engine.dispose()
