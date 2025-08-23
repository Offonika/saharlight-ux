from typing import Any

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services import profile as profile_service
from services.api.app.services.profile import _validate_profile
from services.api.app.diabetes.services.db import Base, Profile, User


def test_validate_profile_allows_target_between_limits() -> None:
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=5.0,
        low=4.0,
        high=7.0,
    )
    _validate_profile(data)


@pytest.mark.parametrize("target", [3.0, 8.0])
def test_validate_profile_rejects_target_outside_limits(target: Any) -> None:
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=target,
        low=4.0,
        high=7.0,
    )
    with pytest.raises(ValueError) as exc:
        _validate_profile(data)
    assert str(exc.value) == "target must be between low and high"


@pytest.mark.asyncio
async def test_save_profile_sos_fields(monkeypatch: pytest.MonkeyPatch) -> None:
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
        cf=1.0,
        target=5.0,
        low=4.0,
        high=7.0,
        sosContact="@alice",
        sosAlertsEnabled=False,
    )
    await profile_service.save_profile(data)
    with TestSession() as session:
        profile = session.get(Profile, 1)
        assert profile is not None
        assert profile.sos_contact == "@alice"
        assert profile.sos_alerts_enabled is False
