import logging
from collections.abc import Generator
from datetime import datetime, time, timezone
from typing import Any, Callable, cast
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app import config, reminder_events
from services.api.app.diabetes.handlers import reminder_handlers
from services.api.app.diabetes.services.db import Base, Reminder, User
from services.api.app.routers import reminders as reminders_router
from services.api.app.routers.reminders import router
from services.api.app.services import reminders
from services.api.app.telegram_auth import check_token


class DummyJob:
    def __init__(self, name: str, data: dict[str, Any] | None = None) -> None:
        self.name = name
        self.data = data
        self.removed = False

    def schedule_removal(self) -> None:  # pragma: no cover - simple flag setter
        self.removed = True


class DummyScheduler:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def add_job(
        self,
        func: Any,
        *,
        trigger: str,
        id: str,
        name: str,
        replace_existing: bool,
        timezone: object,
        kwargs: dict[str, Any] | None = None,
        **params: Any,
    ) -> DummyJob:
        if replace_existing:
            self.jobs = [j for j in self.jobs if j.name != name]
        job = DummyJob(name, kwargs.get("context") if kwargs else None)
        self.jobs.append(job)
        return job


class DummyJobQueue:
    def __init__(self) -> None:
        self.scheduler = DummyScheduler()

    def run_daily(
        self,
        callback: Callable[..., Any],
        time: Any,
        *,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> DummyJob:
        params: dict[str, Any] = {"hour": time.hour, "minute": time.minute}
        if days != (0, 1, 2, 3, 4, 5, 6):
            params["day_of_week"] = ",".join(str(d) for d in days)
        return self.scheduler.add_job(
            callback,
            trigger="cron",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=getattr(time, "tzinfo", None) or ZoneInfo("UTC"),
            kwargs={"context": data},
            **params,
        )

    def run_repeating(
        self,
        callback: Callable[..., Any],
        interval: Any,
        *,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> DummyJob:
        minutes = int(interval.total_seconds() / 60)
        return self.scheduler.add_job(
            callback,
            trigger="interval",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=ZoneInfo("UTC"),
            kwargs={"context": data},
            minutes=minutes,
        )

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.scheduler.jobs if j.name == name]


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
    app.dependency_overrides[check_token] = lambda: {"id": 1}
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
    reminder_events.register_job_queue(cast(Any, job_queue))
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[check_token] = lambda: {"id": 1}
    with TestClient(app) as test_client:
        yield test_client, job_queue
    reminder_events.register_job_queue(None)


def test_empty_returns_200(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == []


def test_nonempty_returns_list(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
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
        session.add(User(telegram_id=1, thread_id="t"))
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
    fastapi_app.dependency_overrides[check_token] = lambda: {"id": 2}
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
        session.add(User(telegram_id=1, thread_id="t"))
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
        session.add(User(telegram_id=1, thread_id="t"))
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
        session.add(User(telegram_id=1, thread_id="t"))
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
        session.add(User(telegram_id=1, thread_id="t"))
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
        session.add(User(telegram_id=1, thread_id="t"))
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


def test_post_reminder_sends_event_without_job_queue(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reminder_events.register_job_queue(None)
    events: list[tuple[str, int]] = []

    async def fake_post(action: str, rid: int) -> None:
        events.append((action, rid))

    monkeypatch.setattr(reminders_router, "_post_job_queue_event", fake_post)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
    resp = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar", "time": "08:00", "isEnabled": True},
    )
    assert resp.status_code == 200
    rid = resp.json()["id"]
    assert events == [("saved", rid)]


def test_patch_reminder_sends_event_without_job_queue(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reminder_events.register_job_queue(None)
    events: list[tuple[str, int]] = []

    async def fake_post(action: str, rid: int) -> None:
        events.append((action, rid))

    monkeypatch.setattr(reminders_router, "_post_job_queue_event", fake_post)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
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
    assert events == [("saved", 1)]


def test_delete_reminder_sends_event_without_job_queue(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reminder_events.register_job_queue(None)
    events: list[tuple[str, int]] = []

    async def fake_post(action: str, rid: int) -> None:
        events.append((action, rid))

    monkeypatch.setattr(reminders_router, "_post_job_queue_event", fake_post)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()
    resp = client.delete("/api/reminders", params={"telegramId": 1, "id": 1})
    assert resp.status_code == 200
    assert events == [("deleted", 1)]


@pytest.mark.asyncio
async def test_post_job_queue_event_logs_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    reminder_events.register_job_queue(None)
    monkeypatch.setenv("API_URL", "http://example.com")
    config.reload_settings()

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            pass

        async def post(self, url: str, json: dict[str, int]) -> httpx.Response:
            req = httpx.Request("POST", url)
            return httpx.Response(500, request=req, text="fail")

    monkeypatch.setattr(reminders_router.httpx, "AsyncClient", lambda: DummyClient())

    with caplog.at_level(logging.ERROR):
        await reminders_router._post_job_queue_event("saved", 1)

    assert "failed to notify job queue" in caplog.text
    monkeypatch.delenv("API_URL")
    config.reload_settings()


@pytest.mark.asyncio
async def test_post_job_queue_event_requires_api_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reminder_events.register_job_queue(None)
    monkeypatch.setenv("API_URL", "")
    config.reload_settings()

    with pytest.raises(RuntimeError, match="API_URL not configured"):
        await reminders_router._post_job_queue_event("saved", 1)

    monkeypatch.delenv("API_URL")
    config.reload_settings()


def test_post_reminder_handles_notify_error(
    client_with_job_queue: tuple[TestClient, DummyJobQueue],
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = client_with_job_queue

    async def boom(_: int) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(reminder_events, "notify_reminder_saved", boom)

    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    resp = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar", "time": "08:00"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_post_job_queue_event_success(monkeypatch: pytest.MonkeyPatch) -> None:
    reminder_events.register_job_queue(object())
    called: list[int] = []

    async def fake_notify(rid: int) -> None:
        called.append(rid)

    monkeypatch.setattr(reminder_events, "notify_reminder_saved", fake_notify)
    await reminders_router._post_job_queue_event("saved", 1)
    assert called == [1]
    reminder_events.register_job_queue(None)


@pytest.mark.asyncio
async def test_post_job_queue_event_handles_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    reminder_events.register_job_queue(object())

    class Boom(reminders_router.ReminderError):
        pass

    async def boom_notify(_: int) -> None:
        raise Boom("fail")

    monkeypatch.setattr(reminder_events, "notify_reminder_saved", boom_notify)
    with caplog.at_level(logging.ERROR):
        await reminders_router._post_job_queue_event("saved", 1)

    assert "failed to notify job queue" in caplog.text
    reminder_events.register_job_queue(None)
