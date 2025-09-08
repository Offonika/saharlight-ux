import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from services.api.app.diabetes.services.db import Profile
from services.api.app.services import profile as profile_service


@pytest.mark.asyncio
async def test_get_profile_operational_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run_db(*args: object, **kwargs: object) -> Profile | None:
        raise OperationalError("stmt", {}, Exception("db down"))

    monkeypatch.setattr(profile_service.db, "run_db", _run_db)

    with pytest.raises(HTTPException) as excinfo:
        await profile_service.get_profile(1)

    assert excinfo.value.status_code == 503
    assert excinfo.value.detail == "database temporarily unavailable"


@pytest.mark.asyncio
async def test_get_profile_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run_db(*args: object, **kwargs: object) -> Profile | None:
        raise RuntimeError("boom")

    monkeypatch.setattr(profile_service.db, "run_db", _run_db)
    with pytest.raises(RuntimeError):
        await profile_service.get_profile(1)


@pytest.mark.asyncio
async def test_get_profile_sqlalchemy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run_db(*args: object, **kwargs: object) -> Profile | None:
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(profile_service.db, "run_db", _run_db)

    with pytest.raises(HTTPException) as excinfo:
        await profile_service.get_profile(1)

    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "database error"
