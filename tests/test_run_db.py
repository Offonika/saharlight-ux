from types import SimpleNamespace
from typing import Any

import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import run_db


@pytest.mark.asyncio
async def test_run_db_sqlite_in_memory(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)

    called = False

    async def fake_to_thread(fn: Any, *args: Any, **kwargs: Any) -> None:
        nonlocal called
        called = True
        return fn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    def work(session: Any) -> None:
        return 42

    result = await run_db(work, sessionmaker=Session)
    assert result == 42
    assert called is False


@pytest.mark.asyncio
async def test_run_db_postgres(monkeypatch: Any) -> None:
    dummy_engine = SimpleNamespace(url=SimpleNamespace(drivername="postgresql", database="db"))

    class DummySession:
        def get_bind(self) -> None:
            return dummy_engine

        def __enter__(self) -> None:
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            pass

    def dummy_sessionmaker() -> None:
        return DummySession()

    called = False

    async def fake_to_thread(fn: Any, *args: Any, **kwargs: Any) -> None:
        nonlocal called
        called = True
        return fn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    def work(session: Any) -> None:
        return 42

    result = await run_db(work, sessionmaker=dummy_sessionmaker)
    assert result == 42
    assert called is True


@pytest.mark.asyncio
async def test_run_db_without_engine() -> None:
    Session = sessionmaker()

    def work(session: Any) -> None:
        return 42

    with pytest.raises(RuntimeError, match="init_db"):
        await run_db(work, sessionmaker=Session)
