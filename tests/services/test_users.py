import logging

import pytest

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

    assert "Failed to ensure user 1 exists" in caplog.text
