import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.services.db as db
from services.api.app.diabetes.services.db import Base, User
from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_save_profile_saves_computed_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        low=4.0,
        high=6.0,
    )
    await profile_service.save_profile(data)
    prof = await profile_service.get_profile(1)
    assert prof is not None
    assert prof.target_bg == 5.0
    engine.dispose()
