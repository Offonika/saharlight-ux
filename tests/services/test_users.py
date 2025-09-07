import logging

import pytest
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services import users


@pytest.mark.asyncio
async def test_ensure_user_exists_db_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def failing_run_db(*args: object, **kwargs: object) -> None:
        raise RuntimeError("db fail")

    monkeypatch.setattr(users, "run_db", failing_run_db)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await users.ensure_user_exists(1)

    assert "Failed to ensure user" not in caplog.text


@pytest.mark.asyncio
async def test_ensure_user_exists_commit_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    in_memory_db: sessionmaker,
) -> None:
    def failing_commit(session: object) -> None:
        raise users.CommitError

    monkeypatch.setattr(users, "commit", failing_commit)
    monkeypatch.setattr(users, "SessionLocal", in_memory_db)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(users.CommitError):
            await users.ensure_user_exists(1)

    assert "Failed to create user 1" in caplog.text
