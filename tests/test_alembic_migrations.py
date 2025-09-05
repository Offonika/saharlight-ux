from __future__ import annotations

from pathlib import Path
import logging.config as logging_config

from alembic import command
from alembic.config import Config
import pytest


@pytest.mark.xfail(
    reason="SQLite migrations not yet supported; TODO fix by 2025-12-31", strict=True
)
def test_alembic_migrations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run Alembic migrations against a temporary SQLite database."""
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Alembic's ``command.upgrade`` configures logging via ``fileConfig`` which
    # by default disables any loggers that already exist.  That side effect
    # leaks into the remainder of the test suite and breaks ``caplog`` based
    # assertions.  Ensure existing loggers remain enabled during this test.
    original_file_config = logging_config.fileConfig

    def _safe_file_config(fname: str, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("disable_existing_loggers", False)
        original_file_config(fname, *args, **kwargs)

    monkeypatch.setattr(logging_config, "fileConfig", _safe_file_config)

    config = Config("services/api/alembic.ini")
    command.upgrade(config, "head")
