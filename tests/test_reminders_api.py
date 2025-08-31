import pytest
from collections.abc import Generator
from datetime import datetime, time, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Any, cast

from services.api.app.diabetes.services.db import Base, Reminder, User
from services.api.app.routers.reminders import router
from services.api.app.services import reminders
from services.api.app.telegram_auth import require_tg_user
from services.api.app import reminder_events
from services.api.app.diabetes.handlers import reminder_handlers


class DummyJob:
    def __init__(
        self, name: str, data: dict[str, Any] | None = None, when: Any = None
    ) -> None:
        self.name = name
        self.data = data
        self.time = when
        self.removed = False

    def schedule_removal(self) -> None:  # pragma: no cover - simple flag setter
        self.removed = True


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_daily(
        self,
        callback: Any,
        time: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(name or "", data, time)
        self.jobs.append(job)
        return job

    def run_repeating(
        self,
        callback: Any,
        interval: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(name or "", data)
        self.jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.jobs if j.name == name]


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.fixture()
def client(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    monkeypatch.setattr(
        reminders,
        "compute_next",
        lambda rem, tz: datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_with_job_queue(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Generator[tuple[TestClient, DummyJobQueue], None, None]:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_events, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(
        reminders,
        "compute_next",
        lambda rem, tz: datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    job_queue = DummyJobQueue()
    reminder_events.set_job_queue(cast(Any, job_queue))
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
    with TestClient(app) as test_client:
        yield test_client, job_queue
    reminder_events.set_job_queue(None)


def test_empty_returns_200(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == []


def test_nonempty_returns_list(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                title="Sugar check",
                time=time(8, 0),
                interval_hours=3,
                interval_minutes=180,
            )
        )
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "telegramId": 1,
            "id": 1,
            "type": "sugar",
            "title": "Sugar check",
            "kind": "at_time",
            "time": "08:00",
            "intervalHours": 3,
            "intervalMinutes": 180,
            "minutesAfter": None,
            "daysOfWeek": None,
            "isEnabled": True,
            "orgId": None,
            "nextAt": "2023-01-01T00:00:00+00:00",
            "lastFiredAt": None,
            "fires7d": 0,
        }
    ]


def test_get_single_reminder(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                title="Sugar check",
                time=time(8, 0),
                interval_hours=3,
                interval_minutes=180,
            )
        )
        session.commit()
    resp = client.get("/api/reminders/1", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == {
        "telegramId": 1,
        "id": 1,
        "type": "sugar",
        "title": "Sugar check",
        "kind": "at_time",
        "time": "08:00",
        "intervalHours": 3,
        "intervalMinutes": 180,
        "minutesAfter": None,
        "daysOfWeek": None,
        "isEnabled": True,
        "orgId": None,
        "nextAt": "2023-01-01T00:00:00+00:00",
        "lastFiredAt": None,
        "fires7d": 0,
    }


def test_invalid_telegram_id_returns_empty_list(client: TestClient) -> None:
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.get("/api/reminders", params={"telegramId": 2})
    assert resp.status_code == 200
    assert resp.json() == []


def test_mismatched_telegram_id_returns_404(client: TestClient) -> None:
    resp = client.get("/api/reminders", params={"telegramId": 2})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "reminder not found"}


def test_get_single_reminder_not_found(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.get("/api/reminders/1", params={"telegramId": 1})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "reminder not found"}


def test_patch_updates_reminder(
    client_with_job_queue: tuple[TestClient, DummyJobQueue],
    session_factory: sessionmaker[Session],
) -> None:
    client, _ = client_with_job_queue
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                title="Old",
                time=time(8, 0),
                interval_hours=3,
            )
        )
        session.commit()
    resp = client.patch(
        "/api/reminders",
        json={
            "telegramId": 1,
            "id": 1,
            "type": "sugar",
            "time": "09:00",
            "intervalMinutes": 180,
            "isEnabled": True,
            "title": "New",
        },
    )
    assert resp.status_code == 200
    with session_factory() as session:
        rem = session.get(Reminder, 1)
        assert rem is not None
        assert rem.time == time(9, 0)
        assert rem.title == "New"
        assert rem.interval_minutes == 180
        assert rem.interval_hours is None


def test_delete_reminder(
    client_with_job_queue: tuple[TestClient, DummyJobQueue],
    session_factory: sessionmaker[Session],
) -> None:
    client, job_queue = client_with_job_queue
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()
    job_queue.run_daily(lambda: None, time(8, 0), name="reminder_1")
    resp = client.delete("/api/reminders", params={"telegramId": 1, "id": 1})
    assert resp.status_code == 200
    with session_factory() as session:
        assert session.get(Reminder, 1) is None
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert jobs
    assert jobs[0].removed


def test_post_reminder_schedules_job(
    client_with_job_queue: tuple[TestClient, DummyJobQueue],
    session_factory: sessionmaker[Session],
) -> None:
    client, job_queue = client_with_job_queue
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar", "time": "08:00", "isEnabled": True},
    )
    assert resp.status_code == 200
    rid = resp.json()["id"]
    assert job_queue.get_jobs_by_name(f"reminder_{rid}")


def test_patch_reminder_schedules_job(
    client_with_job_queue: tuple[TestClient, DummyJobQueue],
    session_factory: sessionmaker[Session],
) -> None:
    client, job_queue = client_with_job_queue
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()
    resp = client.patch(
        "/api/reminders",
        json={
            "telegramId": 1,
            "id": 1,
            "type": "sugar",
            "time": "09:00",
            "isEnabled": True,
        },
    )
    assert resp.status_code == 200
    assert job_queue.get_jobs_by_name("reminder_1")
