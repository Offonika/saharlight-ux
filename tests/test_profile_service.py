import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator

from services.api.app.diabetes.services.db import Base, User
from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services import profile


@pytest.fixture()
def session_factory() -> Generator[sessionmaker, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_save_profile_persists_sos_fields(session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(profile, "SessionLocal", session_factory)

    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    data = ProfileSchema(
        telegramId=1,
        icr=10.0,
        cf=2.0,
        target=5.0,
        low=3.0,
        high=8.0,
        sosContact="@alice",
        sosAlertsEnabled=False,
    )

    await profile.save_profile(data)
    stored = await profile.get_profile(1)

    assert stored is not None
    assert stored.sos_contact == "@alice"
    assert stored.sos_alerts_enabled is False


@pytest.mark.asyncio
async def test_save_profile_defaults_sos_fields(session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(profile, "SessionLocal", session_factory)

    with session_factory() as session:
        session.add(User(telegram_id=2, thread_id="t"))
        session.commit()

    data = ProfileSchema(
        telegramId=2,
        icr=10.0,
        cf=2.0,
        target=5.0,
        low=3.0,
        high=8.0,
    )

    await profile.save_profile(data)
    stored = await profile.get_profile(2)

    assert stored is not None
    assert stored.sos_contact is None
    assert stored.sos_alerts_enabled is True
