from __future__ import annotations

from collections.abc import Iterator
import asyncio
import sqlite3
import subprocess
from typing import Any, Callable, cast
import warnings
import sys
from types import ModuleType

import pytest
import sqlalchemy

dummy = ModuleType("telegram.ext._basehandler")


class _DummyBaseHandler:  # pragma: no cover - minimal stub
    def __init__(self, *args: object, **kwargs: object) -> None:
        return None

    def __class_getitem__(cls, item: object) -> type[_DummyBaseHandler]:
        return cls


dummy.BaseHandler = _DummyBaseHandler
sys.modules.setdefault("telegram.ext._basehandler", dummy)

warnings.filterwarnings("ignore", category=ResourceWarning, module=r"anyio\.streams\.memory")

from services.api.app.diabetes.services import db as db_module  # noqa: E402

_sqlite_connections: list[sqlite3.Connection] = []
_original_sqlite_connect: Callable[..., sqlite3.Connection] = sqlite3.connect


def _tracking_sqlite_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
    conn = _original_sqlite_connect(*args, **kwargs)
    _sqlite_connections.append(conn)
    return conn


setattr(sqlite3, "connect", _tracking_sqlite_connect)


_engines: list[sqlalchemy.engine.Engine] = []
_original_create_engine: Callable[..., sqlalchemy.engine.Engine] = sqlalchemy.create_engine


def _tracking_create_engine(*args: Any, **kwargs: Any) -> sqlalchemy.engine.Engine:
    engine = _original_create_engine(*args, **kwargs)
    _engines.append(engine)
    return engine


setattr(sqlalchemy, "create_engine", _tracking_create_engine)


class _DummyJob:
    def __init__(self, name: str, data: dict[str, Any] | None = None) -> None:
        self.name = name
        self.data = data
        self.removed = False

    def remove(self) -> None:
        self.removed = True

    def schedule_removal(self) -> None:
        self.remove()


class _DummyScheduler:
    def __init__(self) -> None:
        self.jobs: list[_DummyJob] = []

    def add_job(
        self,
        func: Callable[..., object],
        *,
        trigger: str,
        id: str,
        name: str,
        replace_existing: bool,
        timezone: object,
        kwargs: dict[str, Any] | None = None,
        **params: object,
    ) -> _DummyJob:
        if replace_existing:
            self.jobs = [j for j in self.jobs if j.name != name]
        job = _DummyJob(name, kwargs.get("context") if kwargs else None)
        self.jobs.append(job)
        return job


class _DummyJobQueue:
    def __init__(self) -> None:
        self.scheduler = _DummyScheduler()

    def run_once(
        self,
        callback: Callable[..., object],
        when: object,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: object | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> _DummyJob:
        job_id = job_kwargs.get("id") if job_kwargs else name or ""
        if job_kwargs and job_kwargs.get("replace_existing"):
            self.scheduler.jobs = [j for j in self.scheduler.jobs if j.name != job_id]
        job = _DummyJob(job_id, data)
        self.scheduler.jobs.append(job)
        return job

    def run_repeating(
        self,
        callback: Callable[..., object],
        interval: object,
        *,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: object | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> _DummyJob:
        job_id = job_kwargs.get("id") if job_kwargs else name or ""
        replace_existing = bool(job_kwargs and job_kwargs.get("replace_existing"))
        return self.scheduler.add_job(
            callback,
            trigger="interval",
            id=job_id,
            name=job_id,
            replace_existing=replace_existing,
            timezone=timezone,
            kwargs={"context": data} if data is not None else None,
            seconds=interval,
        )

    def get_jobs_by_name(self, name: str) -> list[_DummyJob]:
        return [j for j in self.scheduler.jobs if j.name == name]

    @property
    def jobs(self) -> list[_DummyJob]:
        return self.scheduler.jobs


@pytest.fixture(autouse=True)
def _dummy_job_queue() -> Iterator[None]:
    from services.api.app import reminder_events

    jq = _DummyJobQueue()
    reminder_events.register_job_queue(cast(Any, jq))
    yield
    reminder_events.register_job_queue(None)


# Avoid real database initialization during tests
db_module.init_db = lambda: None


@pytest.fixture(autouse=True)
def _reset_init_db() -> Iterator[None]:
    yield
    from services.api.app.diabetes.services import db as db_module

    db_module.init_db = lambda: None
    import sys

    main_module = sys.modules.get("services.api.app.main")
    if main_module is not None:
        setattr(main_module, "init_db", db_module.init_db)


@pytest.fixture(autouse=True, scope="session")
def _build_ui_assets() -> Iterator[None]:
    """Build webapp UI if static assets are missing."""
    from services.api.app.main import BASE_DIR, UI_DIR

    repo_root = BASE_DIR.parent

    if not (UI_DIR / "real-file.js").is_file() or not (UI_DIR / "index.html").is_file():
        subprocess.run(["pnpm", "install"], cwd=repo_root, check=True)
        subprocess.run(
            ["pnpm", "--filter", "services/webapp/ui", "run", "build"],
            cwd=repo_root,
            check=True,
        )
    yield


@pytest.fixture(autouse=True, scope="session")
def _close_sqlite_connections() -> Iterator[None]:
    """Ensure that all sqlite3 connections and engines
    are closed after the test session."""

    try:
        yield
    finally:
        setattr(sqlite3, "connect", _original_sqlite_connect)
        for conn in _sqlite_connections:
            conn.close()
        setattr(sqlalchemy, "create_engine", _original_create_engine)
        for engine in _engines:
            engine.dispose()


@pytest.fixture(autouse=True, scope="session")
def _dispose_engine_after_tests() -> Iterator[None]:
    """Dispose the global database engine after the test session."""
    from services.api.app.diabetes.services.db import dispose_engine

    yield
    dispose_engine()


@pytest.fixture(autouse=True, scope="module")
def _dispose_engine_per_module() -> Iterator[None]:
    """Dispose the global database engine after each test module."""
    from services.api.app.diabetes.services.db import dispose_engine

    yield
    dispose_engine()


@pytest.fixture(autouse=True)
def _dispose_openai_clients_after_test() -> Iterator[None]:
    """Dispose OpenAI clients after each test."""
    yield
    from services.api.app.diabetes.services.gpt_client import dispose_openai_clients

    asyncio.run(dispose_openai_clients())
