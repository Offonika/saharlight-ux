import importlib
import logging
import sys

import pytest
from sqlalchemy.exc import SQLAlchemyError


def _reload(module: str) -> object:
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


def test_init_db_logs_and_raises_on_engine_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    _reload("services.api.app.config")
    db = _reload("services.api.app.diabetes.services.db")

    def faulty_create_engine(*args: object, **kwargs: object) -> object:
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(db, "create_engine", faulty_create_engine)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="Failed to initialize database engine"):
            db.init_db()
    assert any(
        "Failed to initialize database engine" in record.getMessage()
        for record in caplog.records
    )
