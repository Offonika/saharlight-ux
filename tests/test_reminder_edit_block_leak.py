from datetime import time
import json
from types import SimpleNamespace
from typing import Any, Callable, Iterator, cast
import warnings
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.services.db import (
    Base,
    User,
    Reminder,
    Entry,
    dispose_engine,
)


@contextmanager
def no_warnings() -> Iterator[None]:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        yield


class DummyMessage:
    def __init__(self, data: str) -> None:
        self.web_app_data: SimpleNamespace = SimpleNamespace(data=data)
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyJobQueue:
    def run_daily(
        self,
        callback: Callable[..., Any],
        time: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> None:
        pass

    def run_repeating(
        self,
        callback: Callable[..., Any],
        interval: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> None:
        pass

    def get_jobs_by_name(self, name: str) -> list[Any]:
        return []


def _setup_db() -> tuple[sessionmaker, Any]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True
            )
        )
        session.commit()
    return TestSession, engine


@pytest.mark.asyncio
async def test_bad_input_does_not_create_entry() -> None:
    TestSession, engine = _setup_db()
    msg = DummyMessage(json.dumps({"id": 1, "type": "sugar", "value": "bad"}))
    update = cast(
        Any,
        SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(Any, SimpleNamespace(job_queue=DummyJobQueue()))
    with no_warnings():
        await handlers.reminder_webapp_save(update, context)
    assert msg.replies and "Неверный формат" in msg.replies[0]
    with TestSession() as session:
        assert session.query(Entry).count() == 0
    with no_warnings():
        dispose_engine(engine)


@pytest.mark.asyncio
async def test_good_input_updates_and_ends() -> None:
    TestSession, engine = _setup_db()
    msg = DummyMessage(json.dumps({"id": 1, "type": "sugar", "value": "09:30"}))
    update = cast(
        Any,
        SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(Any, SimpleNamespace(job_queue=DummyJobQueue()))
    with no_warnings():
        await handlers.reminder_webapp_save(update, context)
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem.time == time(9, 30)
        assert session.query(Entry).count() == 0
    with no_warnings():
        dispose_engine(engine)
