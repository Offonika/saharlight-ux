import logging
import pytest
from sqlalchemy.exc import SQLAlchemyError
import asyncio

import services.bot.main as bot


def test_main_logs_db_error(monkeypatch, caplog):
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")

    def faulty_init_db():
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(bot, "init_db", faulty_init_db)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            asyncio.run(bot.main())

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
