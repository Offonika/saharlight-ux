from __future__ import annotations

import logging
import logging.config

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
import pytest


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_upgrade_head(monkeypatch: pytest.MonkeyPatch) -> None:
    """Migrations upgrade cleanly to head on an in-memory SQLite DB."""
    db_url = "sqlite+pysqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", db_url)

    original_file_config = logging.config.fileConfig

    def _safe_file_config(fname: str, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("disable_existing_loggers", False)
        original_file_config(fname, *args, **kwargs)

    monkeypatch.setattr(logging.config, "fileConfig", _safe_file_config)

    engine = create_engine(db_url, future=True)
    with engine.connect() as connection:
        cfg = Config("services/api/alembic.ini")
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
