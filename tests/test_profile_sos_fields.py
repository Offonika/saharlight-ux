import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import Base, User
from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_save_profile_stores_sos_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(profile_service, "SessionLocal", TestSession)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=2.0,
        target=3.0,
        low=1.0,
        high=5.0,
        sosContact="112",
        sosAlertsEnabled=False,
    )
    await profile_service.save_profile(data)
    prof = await profile_service.get_profile(1)
    assert prof is not None
    assert prof.sos_contact == "112"
    assert prof.sos_alerts_enabled is False
    engine.dispose()


@pytest.mark.asyncio
async def test_save_profile_defaults_sos_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(profile_service, "SessionLocal", TestSession)
    with TestSession() as session:
        session.add(User(telegram_id=2, thread_id="t", timezone="UTC"))
        session.commit()
    data = ProfileSchema(
        telegramId=2,
        icr=1.0,
        cf=2.0,
        target=3.0,
        low=1.0,
        high=5.0,
    )
    await profile_service.save_profile(data)
    prof = await profile_service.get_profile(2)
    assert prof is not None
    assert prof.sos_contact == ""
    assert prof.sos_alerts_enabled is True
    engine.dispose()
