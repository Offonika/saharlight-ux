from __future__ import annotations

from collections.abc import Iterator
import sqlite3
import subprocess
from typing import Any, Callable, cast
import warnings
import sys
from types import ModuleType

import asyncio
import pytest
import sqlalchemy
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes import learning_handlers as _dynamic_learning_handlers

pytest_plugins = ("pytest_asyncio",)

# Ensure dynamic learning handlers expose ``curriculum_engine`` for tests that
# monkeypatch it.
setattr(_dynamic_learning_handlers, "curriculum_engine", curriculum_engine)


@pytest.fixture(scope="session", autouse=True)
def _import_openai_utils() -> None:
    """Import ``openai_utils`` once to register its side effects."""
    import importlib

    importlib.import_module("services.api.app.diabetes.utils.openai_utils")


@pytest.fixture(autouse=True)
def _fake_learning_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub profile lookups to avoid external API calls in tests."""

    class _StubProfiles:
        async def get_profile_for_user(
            self, _user_id: int, _ctx: object
        ) -> dict[str, object]:
            return {}

    monkeypatch.setattr(_dynamic_learning_handlers, "profiles", _StubProfiles())

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
    from services.api.app.routers.webapp import BASE_DIR, UI_DIR

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


@pytest.fixture()
def in_memory_db(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker[Session]]:
    """Provide an in-memory SQLite database for tests."""

    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    db_module.Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db_module, "SessionLocal", TestSession)
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker[Session]]:
    """Configure ``SessionLocal`` with an in-memory SQLite engine.

    The fixture patches the application settings to use an in-memory
    SQLite database, calls :func:`init_db` to create all tables and then
    replaces ``SessionLocal`` in already imported modules.  Tests can
    depend on this fixture to get a fresh sessionmaker that is isolated
    from the real database.
    """

    import importlib
    from services.api.app.diabetes.services import db as db_module

    # ``init_db`` is stubbed globally for tests. Reload the module to restore
    # the real implementation before configuring an in-memory database.
    db = importlib.reload(db_module)

    # Import models with additional tables to register them in Base metadata.
    import services.api.app.diabetes.models_learning as ml_models
    import services.api.app.assistant.models as as_models
    importlib.reload(ml_models)
    importlib.reload(as_models)

    # Ensure the database URL points to an in-memory SQLite instance. Use a
    # ``StaticPool`` so that the in-memory database persists across multiple
    # connections.
    from sqlalchemy.pool import StaticPool
    import sqlalchemy

    def _memory_engine(url: str, *args: object, **kwargs: object) -> sqlalchemy.engine.Engine:
        kwargs.setdefault("connect_args", {"check_same_thread": False})
        kwargs.setdefault("poolclass", StaticPool)
        engine = _original_create_engine(url, *args, **kwargs)
        _engines.append(engine)
        return engine

    monkeypatch.setattr(sqlalchemy, "create_engine", _memory_engine)
    monkeypatch.setattr(db.settings, "database_url", "sqlite:///:memory:", raising=False)

    # Initialise the database engine and create schema.
    db.init_db()
    db.Base.metadata.create_all(bind=db.engine)

    session_factory = db.SessionLocal

    # Replace ``SessionLocal`` in all loaded modules so that code which
    # imported it directly uses the in-memory session as well.
    for name, module in list(sys.modules.items()):
        if name.startswith(("services.", "tests.")) and hasattr(module, "SessionLocal"):
            monkeypatch.setattr(module, "SessionLocal", session_factory, raising=False)

    try:
        yield session_factory
    finally:
        db.dispose_engine()


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


@pytest.fixture(scope="session", autouse=True)
def _stub_openai_clients() -> Iterator[None]:
    """Stub OpenAI clients to avoid real network calls."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    mp.setenv("OPENAI_API_KEY", "dummy-key")
    mp.setenv("OPENAI_ASSISTANT_ID", "asst_dummy")

    from services.api.app.diabetes.utils import openai_utils
    from services.api.app.diabetes.services import gpt_client

    class _SyncClient:
        def close(self) -> None:  # pragma: no cover - trivial
            return None

    class _AsyncClient:
        async def close(self) -> None:  # pragma: no cover - trivial
            return None

    def _get_sync() -> _SyncClient:
        return _SyncClient()

    def _get_async() -> _AsyncClient:
        return _AsyncClient()

    mp.setattr(openai_utils, "get_openai_client", _get_sync)
    mp.setattr(openai_utils, "get_async_openai_client", _get_async)
    mp.setattr(gpt_client, "get_openai_client", _get_sync)
    mp.setattr(gpt_client, "get_async_openai_client", _get_async)
    try:
        yield
    finally:
        mp.undo()


@pytest.fixture(autouse=True)
def _dispose_openai_clients_after_test() -> Iterator[None]:
    """Dispose OpenAI clients after each test."""
    yield
    from services.api.app.diabetes.services.gpt_client import dispose_openai_clients

    asyncio.run(dispose_openai_clients())
