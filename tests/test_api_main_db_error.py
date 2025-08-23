import importlib
import logging

import pytest
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.diabetes.services import db


def test_main_logs_db_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import services.api.app.main as main

    def faulty_init_db() -> None:
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db, "init_db", faulty_init_db)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="Database initialization failed"):
            importlib.reload(main)
    assert any(
        "Failed to initialize the database" in record.getMessage()
        for record in caplog.records
    )

    monkeypatch.setattr(db, "init_db", lambda: None)
    importlib.reload(main)
