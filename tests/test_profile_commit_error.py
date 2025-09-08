import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.services.db as db
from services.api.app.diabetes.services.db import Base
from services.api.app.schemas.profile import ProfileUpdateSchema
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_save_profile_commit_error_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)

    def fail_commit(_: object) -> None:
        raise profile_service.CommitError

    monkeypatch.setattr(profile_service, "commit", fail_commit)

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

    assert exc.value.status_code == 503
    assert exc.value.detail == "временные проблемы с БД"
    engine.dispose()
