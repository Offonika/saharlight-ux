from __future__ import annotations

from collections.abc import Iterator
import sqlite3
import subprocess
from typing import Any, Callable
import warnings

import pytest
import sqlalchemy
from services.api.app.diabetes.services import db as db_module

warnings.filterwarnings(
    "ignore", category=ResourceWarning, module=r"anyio\.streams\.memory"
)

_sqlite_connections: list[sqlite3.Connection] = []
_original_sqlite_connect: Callable[..., sqlite3.Connection] = sqlite3.connect


def _tracking_sqlite_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
    conn = _original_sqlite_connect(*args, **kwargs)
    _sqlite_connections.append(conn)
    return conn


setattr(sqlite3, "connect", _tracking_sqlite_connect)


_engines: list[sqlalchemy.engine.Engine] = []
_original_create_engine: Callable[..., sqlalchemy.engine.Engine] = (
    sqlalchemy.create_engine
)


def _tracking_create_engine(*args: Any, **kwargs: Any) -> sqlalchemy.engine.Engine:
    engine = _original_create_engine(*args, **kwargs)
    _engines.append(engine)
    return engine


setattr(sqlalchemy, "create_engine", _tracking_create_engine)

# Avoid real database initialization during tests
db_module.init_db = lambda: None


@pytest.fixture(autouse=True, scope="session")
def _build_ui_assets() -> Iterator[None]:
    """Build webapp UI if static assets are missing."""
    from services.api.app.main import BASE_DIR, UI_DIR

    repo_root = BASE_DIR.parent

    if not (UI_DIR / "real-file.js").is_file():
        subprocess.run(["pnpm", "install"], cwd=repo_root, check=True)
        subprocess.run(
            ["pnpm", "--filter", "services/webapp/ui", "run", "build"],
            cwd=repo_root,
            check=True,
        )
    yield


@pytest.fixture(autouse=True, scope="session")
def _close_sqlite_connections() -> Iterator[None]:
    """Ensure that all sqlite3 connections and engines are closed after the test session."""

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
