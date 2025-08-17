from collections.abc import Iterator
import sqlite3
from typing import Any, Callable
import warnings

import pytest

warnings.filterwarnings(
    "ignore", category=ResourceWarning, module=r"anyio\.streams\.memory"
)


@pytest.fixture(autouse=True, scope="session")
def _close_sqlite_connections() -> Iterator[None]:
    """Ensure that all sqlite3 connections are closed after the test session."""

    connections: list[sqlite3.Connection] = []
    original_connect: Callable[..., sqlite3.Connection] = sqlite3.connect

    def tracking_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        conn = original_connect(*args, **kwargs)
        connections.append(conn)
        return conn

    sqlite3.connect = tracking_connect  # type: ignore[assignment]
    try:
        yield
    finally:
        sqlite3.connect = original_connect  # type: ignore[assignment]
        for conn in connections:
            conn.close()


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
