from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories.progress import (
    get_progress,
    upsert_progress,
)
from services.api.app.diabetes.services import db


@pytest.fixture()
def setup_db() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.commit()


@pytest.mark.asyncio
async def test_upsert_and_get_progress(setup_db: None) -> None:
    await upsert_progress(1, 10, 1)
    progress = await get_progress(1, 10)
    assert progress is not None
    assert progress.current_step == 1

    await upsert_progress(1, 10, 2)
    updated = await get_progress(1, 10)
    assert updated is not None
    assert updated.current_step == 2
