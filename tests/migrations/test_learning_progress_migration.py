from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import importlib
from typing import Any

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.dialects import postgresql
import pytest


def test_learning_progress_upgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "db.sqlite3"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config("services/api/alembic.ini")
    command.upgrade(cfg, "20251006_add_learning_progress")

    engine = sa.create_engine(url)
    inspector = sa.inspect(engine)

    tables = inspector.get_table_names()
    assert "learning_plans" in tables
    assert "learning_progress" in tables

    lp_cols = {c["name"]: c for c in inspector.get_columns("learning_plans")}
    assert set(lp_cols) == {
        "id",
        "user_id",
        "is_active",
        "version",
        "plan_json",
        "created_at",
        "updated_at",
    }
    assert lp_cols["is_active"]["default"] == "true"
    assert lp_cols["version"]["default"] == "1"
    assert lp_cols["plan_json"]["nullable"] is False
    assert lp_cols["created_at"]["default"] == "CURRENT_TIMESTAMP"

    lp_indexes = inspector.get_indexes("learning_plans")
    assert any(
        ix["name"] == "ix_learning_plans_user_id_is_active"
        and ix["column_names"] == ["user_id", "is_active"]
        for ix in lp_indexes
    )

    lpr_cols = {c["name"]: c for c in inspector.get_columns("learning_progress")}
    assert set(lpr_cols) == {
        "id",
        "user_id",
        "plan_id",
        "progress_json",
        "created_at",
        "updated_at",
    }
    assert lpr_cols["progress_json"]["default"] == "'{}'"
    assert lpr_cols["progress_json"]["nullable"] is False
    assert lpr_cols["created_at"]["default"] == "CURRENT_TIMESTAMP"
    assert lpr_cols["updated_at"]["default"] == "CURRENT_TIMESTAMP"

    lpr_indexes = inspector.get_indexes("learning_progress")
    assert any(
        ix["name"] == "ix_learning_progress_user_id_plan_id"
        and ix["column_names"] == ["user_id", "plan_id"]
        for ix in lpr_indexes
    )
    assert any(
        ix["name"] == "ix_learning_progress_updated_at"
        and ix["column_names"] == ["updated_at"]
        for ix in lpr_indexes
    )

    engine.dispose()


def test_learning_progress_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    actions: list[tuple[str, tuple[sa.Column[Any, Any], ...]]] = []
    indexes: list[tuple[str, str, list[str]]] = []

    def create_table(name: str, *cols: sa.Column[Any, Any], **kw: object) -> None:
        actions.append((name, cols))

    def create_index(name: str, table: str, cols: list[str], **kw: object) -> None:
        indexes.append((name, table, cols))

    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    revs = [
        "20251005_add_learning_plans",
        "20251006_add_learning_progress",
    ]
    for rev in revs:
        mod = importlib.import_module(f"services.api.alembic.versions.{rev}")
        monkeypatch.setattr(mod.op, "get_bind", lambda: bind)
        monkeypatch.setattr(mod.op, "create_table", create_table)
        monkeypatch.setattr(mod.op, "create_index", create_index)
        mod.upgrade()

    lp_cols = {c.name: c for t, cols in actions if t == "learning_plans" for c in cols}
    lpr_cols = {c.name: c for t, cols in actions if t == "learning_progress" for c in cols}
    assert isinstance(
        lp_cols["plan_json"].type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )
    assert isinstance(
        lpr_cols["progress_json"].type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )
    assert str(lpr_cols["progress_json"].server_default.arg) == "'{}'"

    assert ("ix_learning_plans_user_id_is_active", "learning_plans", ["user_id", "is_active"]) in indexes
    assert ("ix_learning_progress_user_id_plan_id", "learning_progress", ["user_id", "plan_id"]) in indexes
    assert ("ix_learning_progress_updated_at", "learning_progress", ["updated_at"]) in indexes
