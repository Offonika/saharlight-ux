from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest


def _run_migration(
    fn_name: str, monkeypatch: pytest.MonkeyPatch
) -> list[str]:
    migration = importlib.import_module(
        "services.api.alembic.versions.20251008_recreate_lesson_logs"
    )
    actions: list[str] = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        migration.op, "drop_index", lambda name, **kw: actions.append(f"drop_index:{name}")
    )
    monkeypatch.setattr(
        migration.op,
        "alter_column",
        lambda table, column_name, **kw: actions.append(f"alter_column:{column_name}"),
    )
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: actions.append(f"add_column:{column.name}"),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_column",
        lambda table, column_name: actions.append(f"drop_column:{column_name}"),
    )
    monkeypatch.setattr(
        migration.op, "execute", lambda sql, *a, **k: actions.append("execute")
    )
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, table, cols: actions.append(f"create_index:{name}"),
    )
    monkeypatch.setattr(
        migration.op, "drop_table", lambda *a, **k: actions.append("drop_table")
    )
    getattr(migration, fn_name)()
    return actions


def test_upgrade_does_not_drop_table(monkeypatch: pytest.MonkeyPatch) -> None:
    actions = _run_migration("upgrade", monkeypatch)
    assert "drop_table" not in actions


def test_downgrade_does_not_drop_table(monkeypatch: pytest.MonkeyPatch) -> None:
    actions = _run_migration("downgrade", monkeypatch)
    assert "drop_table" not in actions

