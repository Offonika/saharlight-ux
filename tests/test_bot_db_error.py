import logging
import pytest
from sqlalchemy.exc import SQLAlchemyError

import bot


def test_main_logs_db_error(monkeypatch, caplog):
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")

    def faulty_init_db():
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(bot, "init_db", faulty_init_db)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            bot.main()

    assert exc.value.code == 1
    assert any(
        "Failed to initialize the database" in record.getMessage()
        for record in caplog.records
    )
