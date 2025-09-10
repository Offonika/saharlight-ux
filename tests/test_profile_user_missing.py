import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.services.db as db
from services.api.app.diabetes.services.db import Base
from services.api.app.diabetes.schemas.profile import ProfileSettingsIn
from services.api.app.schemas.profile import ProfileUpdateSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_save_profile_user_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    data = ProfileUpdateSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=5.0,
        low=4.0,
        high=6.0,
    )
    with pytest.raises(HTTPException) as exc:
        await profile_service.save_profile(data)
    assert exc.value.status_code == 404
    assert exc.value.detail == "user not found"
    engine.dispose()


@pytest.mark.asyncio
async def test_patch_user_settings_user_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    await profile_service.patch_user_settings(1, ProfileSettingsIn(timezone="UTC"))

    with TestSession() as session:
        user = session.get(db.User, 1)
        assert user is not None
        assert user.thread_id == "api"
        assert user.onboarding_complete is True
        profile = session.get(db.Profile, 1)
        assert profile is not None
        assert profile.timezone == "UTC"
    engine.dispose()
