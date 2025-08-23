import logging
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

import services.bot.main as bot


def test_main_logs_db_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(bot.settings, "telegram_token", "token")  # type: ignore[attr-defined]
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")

    def faulty_init_db() -> None:
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(bot, "init_db", faulty_init_db)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            bot.main()

    assert (
        exc.value.code
        == (
            "Database initialization failed. Please check your configuration "
            "and try again."
        )
    )
    assert any(
        "Failed to initialize the database" in record.getMessage()
        for record in caplog.records
    )
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_error_handler_logs_without_stack(
    caplog: pytest.LogCaptureFixture,
) -> None:
    context = SimpleNamespace(error=RuntimeError("boom"))
    with caplog.at_level(logging.ERROR):
        await bot.error_handler(object(), context)

    assert "Exception while handling update" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)