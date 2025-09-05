from __future__ import annotations

import logging
import logging.config

from alembic import command
from alembic.config import Config
import pytest


def test_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    original_file_config = logging.config.fileConfig

    def _safe_file_config(fname: str, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("disable_existing_loggers", False)
        original_file_config(fname, *args, **kwargs)

    monkeypatch.setattr(logging.config, "fileConfig", _safe_file_config)

    cfg = Config("services/api/alembic.ini")
    command.upgrade(cfg, "head")

    logging.config.dictConfig({"version": 1, "disable_existing_loggers": False})
    assert logging.getLogger(__name__).disabled is False
