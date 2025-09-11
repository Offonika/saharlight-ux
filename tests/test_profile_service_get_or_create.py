from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes.services.db import Base, Profile
import services.api.app.services.profile as profile_service


@pytest.mark.asyncio
async def test_get_profile_settings_creates_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, class_=Session
    )

    async def run_db(func, *args, sessionmaker: sessionmaker[Session], **kwargs):
        with sessionmaker() as session:
            return func(session, *args, **kwargs)

    monkeypatch.setattr(profile_service.db, "SessionLocal", TestSession)
    monkeypatch.setattr(profile_service.db, "run_db", run_db)

    settings = await profile_service.get_profile_settings(1)
    assert settings.telegramId == 1
    assert settings.timezone == "UTC"
    assert settings.carbUnits.value == "g"

    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.timezone == "UTC"
        assert profile.carb_units == "g"

    engine.dispose()


@pytest.mark.asyncio
async def test_get_profile_settings_negative_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, class_=Session
    )

    async def run_db(func, *args, sessionmaker: sessionmaker[Session], **kwargs):
        with sessionmaker() as session:
            return func(session, *args, **kwargs)

    monkeypatch.setattr(profile_service.db, "SessionLocal", TestSession)
    monkeypatch.setattr(profile_service.db, "run_db", run_db)

    with pytest.raises(HTTPException) as exc:
        await profile_service.get_profile_settings(-1)
    assert exc.value.status_code == 422

    engine.dispose()
