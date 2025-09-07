from __future__ import annotations

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
