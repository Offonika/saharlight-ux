import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import time as dt_time

import services.api.app.diabetes.services.db as db
from services.api.app.diabetes.services.db import Base, User
from services.api.app.schemas.profile import ProfileUpdateSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_save_profile_stores_quiet_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
    data = ProfileUpdateSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=3.0,
        low=1.0,
        high=5.0,
        quietStart="22:30",
        quietEnd="06:45",
    )
    await profile_service.save_profile(data)
    prof = await profile_service.get_profile(1)
    assert prof is not None
    assert prof.quiet_start == dt_time.fromisoformat("22:30")
    assert prof.quiet_end == dt_time.fromisoformat("06:45")
    engine.dispose()


@pytest.mark.asyncio
async def test_save_profile_defaults_quiet_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    with TestSession() as session:
        session.add(User(telegram_id=2, thread_id="t"))
        session.commit()
    data = ProfileUpdateSchema(
        telegramId=2,
        icr=1.0,
        cf=1.0,
        target=3.0,
        low=1.0,
        high=5.0,
    )
    await profile_service.save_profile(data)
    prof = await profile_service.get_profile(2)
    assert prof is not None
    assert prof.quiet_start == dt_time.fromisoformat("23:00")
    assert prof.quiet_end == dt_time.fromisoformat("07:00")
    engine.dispose()
