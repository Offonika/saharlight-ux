from __future__ import annotations

import asyncio
import contextvars
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.assistant.services import progress_service


@pytest.fixture(autouse=True)
def setup_db(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    conn = engine.raw_connection()
    conn.create_function("greatest", 2, lambda a, b: max(a, b))
    conn.close()
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(progress_service, "SessionLocal", SessionLocal, raising=False)
    db.Base.metadata.create_all(bind=engine)
    yield
    db.dispose_engine(engine)


@pytest.mark.asyncio
async def test_get_progress_none() -> None:
    result = await progress_service.get_progress(1, "intro")
    assert result is None


@pytest.mark.asyncio
async def test_upsert_updates_timestamp() -> None:
    await progress_service.upsert_progress(1, "intro", 1)
    progress = await progress_service.get_progress(1, "intro")
    assert progress is not None
    assert progress.step == 1
    first_ts = progress.updated_at

    time.sleep(1)
    await progress_service.upsert_progress(1, "intro", 2)
    progress2 = await progress_service.get_progress(1, "intro")
    assert progress2 is not None
    assert progress2.step == 2
    assert progress2.updated_at > first_ts


@pytest.mark.asyncio
async def test_upsert_progress_concurrent_keeps_max_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    step_ctx: contextvars.ContextVar[int] = contextvars.ContextVar("step")

    original_commit = progress_service.commit

    def delayed_commit(session: Session) -> None:
        step = step_ctx.get()
        if step == 1:
            time.sleep(0.1)
        original_commit(session)

    monkeypatch.setattr(progress_service, "commit", delayed_commit)

    async def upsert(step: int) -> None:
        token = step_ctx.set(step)
        try:
            await progress_service.upsert_progress(1, "intro", step)
        finally:
            step_ctx.reset(token)

    await asyncio.gather(*(upsert(s) for s in (1, 2, 3)))
    progress = await progress_service.get_progress(1, "intro")
    assert progress is not None
    assert progress.step == 3
