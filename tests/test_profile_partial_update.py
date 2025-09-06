import pytest
from datetime import time as dt_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.services.db as db
from services.api.app.diabetes.services.db import Base, User
from services.api.app.schemas.profile import ProfileUpdateSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_save_profile_does_not_override_missing_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    initial = ProfileUpdateSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=5.0,
        low=4.0,
        high=6.0,
        quietStart=dt_time(1, 0),
        quietEnd=dt_time(2, 0),
        timezone="Europe/Moscow",
        timezoneAuto=False,
        sosAlertsEnabled=False,
    )
    await profile_service.save_profile(initial)

    update = ProfileUpdateSchema(
        telegramId=1,
        icr=1.5,
        cf=1.5,
        target=5.5,
        low=4.5,
        high=6.5,
    )
    await profile_service.save_profile(update)

    prof = await profile_service.get_profile(1)
    assert prof.quiet_start == dt_time(1, 0)
    assert prof.quiet_end == dt_time(2, 0)
    assert prof.timezone == "Europe/Moscow"
    assert prof.timezone_auto is False
    assert prof.sos_alerts_enabled is False
    engine.dispose()
