from collections.abc import Iterator
import sqlite3
from typing import Any, Callable
import warnings

import pytest
import sqlalchemy

warnings.filterwarnings(
    "ignore", category=ResourceWarning, module=r"anyio\.streams\.memory"
)


_sqlite_connections: list[sqlite3.Connection] = []
_original_sqlite_connect: Callable[..., sqlite3.Connection] = sqlite3.connect


def _tracking_sqlite_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
    conn = _original_sqlite_connect(*args, **kwargs)
    _sqlite_connections.append(conn)
    return conn


sqlite3.connect = _tracking_sqlite_connect  # type: ignore[assignment]


_engines: list[sqlalchemy.engine.Engine] = []
_original_create_engine = sqlalchemy.create_engine


def _tracking_create_engine(*args: Any, **kwargs: Any) -> sqlalchemy.engine.Engine:
    engine = _original_create_engine(*args, **kwargs)
    _engines.append(engine)
    return engine


sqlalchemy.create_engine = _tracking_create_engine  # type: ignore[assignment]


@pytest.fixture(autouse=True, scope="session")
def _close_sqlite_connections() -> Iterator[None]:
    """Ensure that all sqlite3 connections and engines are closed after the test session."""

    try:
        yield
    finally:
        sqlite3.connect = _original_sqlite_connect  # type: ignore[assignment]
        for conn in _sqlite_connections:
            conn.close()
        sqlalchemy.create_engine = _original_create_engine  # type: ignore[assignment]
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
