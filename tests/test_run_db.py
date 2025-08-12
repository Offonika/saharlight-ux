from types import SimpleNamespace
from typing import Any

import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import run_db


@pytest.mark.asyncio
async def test_run_db_sqlite_in_memory(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)

    called = False

    async def fake_to_thread(fn, *args: Any, **kwargs: Any) -> Any:
        nonlocal called
        called = True
        return fn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    def work(session):
        return 42

    result = await run_db(work, sessionmaker=Session)
    assert result == 42
    assert called is False


@pytest.mark.asyncio
async def test_run_db_postgres(monkeypatch) -> None:
    dummy_engine = SimpleNamespace(url=SimpleNamespace(drivername="postgresql", database="db"))

    class DummySession:
        def get_bind(self):
            return dummy_engine

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    def dummy_sessionmaker():
        return DummySession()

    called = False

    async def fake_to_thread(fn, *args: Any, **kwargs: Any) -> Any:
        nonlocal called
        called = True
        return fn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    def work(session):
        return 42

    result = await run_db(work, sessionmaker=dummy_sessionmaker)
    assert result == 42
    assert called is True


@pytest.mark.asyncio
async def test_run_db_without_engine() -> None:
    Session = sessionmaker()

    def work(session):
        return 42

    with pytest.raises(RuntimeError, match="init_db"):
        await run_db(work, sessionmaker=Session)
