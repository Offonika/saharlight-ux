from __future__ import annotations

import logging
import logging.config

from types import SimpleNamespace
import importlib
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
    command.upgrade(cfg, "heads")

    logging.config.dictConfig({"version": 1, "disable_existing_loggers": False})
    assert logging.getLogger(__name__).disabled is False


class _DummyBatchOp:
    def __enter__(self) -> "_DummyBatchOp":
        return self

    def __exit__(self, *args: object) -> None:  # pragma: no cover - context cleanup
        return None

    def alter_column(self, *args: object, **kwargs: object) -> None:
        return None

    def drop_column(self, *args: object, **kwargs: object) -> None:
        return None


class _DummyInspector:
    def __init__(self) -> None:
        self.profile_cols = {
            "timezone",
            "timezone_auto",
            "dia",
            "round_step",
            "carb_units",
            "grams_per_xe",
            "therapy_type",
            "glucose_units",
            "insulin_type",
            "prebolus_min",
            "max_bolus",
            "postmeal_check_min",
        }
        self.user_cols = {"timezone_auto"}

    def get_columns(self, table_name: str) -> list[dict[str, str]]:
        cols = self.profile_cols if table_name == "profiles" else self.user_cols
        return [{"name": name} for name in cols]


@pytest.mark.parametrize(
    "dialect, expected",
    [
        ("postgresql", "FROM users AS u"),
        ("sqlite", "SELECT u.timezone_auto"),
    ],
)
def test_timezone_auto_upgrade_sql(
    monkeypatch: pytest.MonkeyPatch, dialect: str, expected: str
) -> None:
    migration = importlib.import_module(
        "services.api.alembic.versions.20250906_move_user_settings_to_profile"
    )

    executed: list[str] = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.op, "add_column", lambda *a, **k: None)
    monkeypatch.setattr(migration.op, "drop_column", lambda *a, **k: None)
    monkeypatch.setattr(migration.op, "batch_alter_table", lambda *a, **k: _DummyBatchOp())
    monkeypatch.setattr(migration.op, "execute", lambda sql, *a, **k: executed.append(str(sql)))
    monkeypatch.setattr(migration.sa, "inspect", lambda b: _DummyInspector())

    migration.upgrade()
    assert expected in executed[0]


@pytest.mark.parametrize(
    "dialect, expected",
    [
        ("postgresql", "FROM profiles AS p"),
        ("sqlite", "SELECT p.timezone_auto"),
    ],
)
def test_timezone_auto_downgrade_sql(
    monkeypatch: pytest.MonkeyPatch, dialect: str, expected: str
) -> None:
    migration = importlib.import_module(
        "services.api.alembic.versions.20250906_move_user_settings_to_profile"
    )

    executed: list[str] = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect))
    monkeypatch.setattr(migration.op, "get_bind", lambda: bind)
    monkeypatch.setattr(migration.op, "add_column", lambda *a, **k: None)
    monkeypatch.setattr(migration.op, "drop_column", lambda *a, **k: None)
    monkeypatch.setattr(migration.op, "batch_alter_table", lambda *a, **k: _DummyBatchOp())
    monkeypatch.setattr(migration.op, "execute", lambda sql, *a, **k: executed.append(str(sql)))
    monkeypatch.setattr(migration.op, "alter_column", lambda *a, **k: None)
    monkeypatch.setattr(migration.sa, "inspect", lambda b: _DummyInspector())

    migration.downgrade()
    assert expected in executed[0]
