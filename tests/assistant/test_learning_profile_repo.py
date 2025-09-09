from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import learning_profile
from services.api.app.diabetes.services import db


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record) -> None:  # pragma: no cover - setup
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    session_local = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(learning_profile, "SessionLocal", session_local)
    return session_local


@pytest.mark.asyncio
async def test_get_missing(session_local: sessionmaker[Session]) -> None:
    assert await learning_profile.get_learning_profile(1) is None


@pytest.mark.asyncio
async def test_upsert_and_update(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()

    await learning_profile.upsert_learning_profile(
        1, age_group="adult", learning_level="novice", diabetes_type="T1"
    )
    profile = await learning_profile.get_learning_profile(1)
    assert profile is not None
    assert profile.age_group == "adult"
    assert profile.learning_level == "novice"
    assert profile.diabetes_type == "T1"

    await learning_profile.upsert_learning_profile(1, learning_level="expert")
    profile2 = await learning_profile.get_learning_profile(1)
    assert profile2 is not None
    assert profile2.learning_level == "expert"
    assert profile2.age_group == "adult"


@pytest.mark.asyncio
async def test_upsert_without_user(session_local: sessionmaker[Session]) -> None:
    with pytest.raises(RuntimeError, match="register"):
        await learning_profile.upsert_learning_profile(2, age_group="adult")
