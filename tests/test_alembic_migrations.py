from __future__ import annotations

from pathlib import Path

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

    config = Config("services/api/alembic.ini")
    command.upgrade(config, "head")
