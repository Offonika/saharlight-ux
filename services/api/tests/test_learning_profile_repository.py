from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Any, Callable

from services.api.app.assistant.repositories import learning_profile
from services.api.app.diabetes.services import db


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


@pytest.mark.asyncio
async def test_upsert_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    SessionLocal = setup_db()

    async def run_db(
        fn: Callable[..., Any],
        *args: Any,
        sessionmaker: sessionmaker[Session] = SessionLocal,
        **kwargs: Any,
    ) -> Any:
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(learning_profile, "run_db", run_db, raising=False)
    monkeypatch.setattr(learning_profile, "SessionLocal", SessionLocal, raising=False)

    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        session.commit()

    await learning_profile.upsert_learning_profile(
        1, age_group="adult", learning_level="novice", diabetes_type="T1"
    )
    profile = await learning_profile.get_learning_profile(1)
    assert profile is not None
    assert profile.age_group == "adult"

    await learning_profile.upsert_learning_profile(1, learning_level="expert")
    profile = await learning_profile.get_learning_profile(1)
    assert profile is not None
    assert profile.learning_level == "expert"
    assert profile.diabetes_type == "T1"
