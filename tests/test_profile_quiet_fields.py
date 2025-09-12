import pytest
from datetime import time as dt_time

from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes.services import db
from services.api.app.schemas.profile import ProfileUpdateSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_save_profile_stores_quiet_fields(
    session_local: sessionmaker[Session],
) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
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


@pytest.mark.asyncio
async def test_save_profile_defaults_quiet_fields(
    session_local: sessionmaker[Session],
) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=2, thread_id="t"))
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
