# test_alembic_env.py

import builtins
import contextlib
import importlib
import logging
import sys
import types
from types import ModuleType
from typing import Any, Iterator

import alembic.context  # type: ignore[import-not-found]
import pytest


def test_env_handles_missing_dotenv(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    original_import = builtins.__import__

    def fake_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "dotenv":
            raise ImportError
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.delitem(sys.modules, "services.api.alembic.env", raising=False)

    dummy_config = types.SimpleNamespace(config_file_name=None)
    monkeypatch.setattr(alembic.context, "config", dummy_config, raising=False)
    monkeypatch.setattr(alembic.context, "is_offline_mode", lambda: True)
    monkeypatch.setattr(alembic.context, "configure", lambda *a, **kw: None)

    @contextlib.contextmanager
    def begin_transaction() -> Iterator[None]:
        yield

    monkeypatch.setattr(alembic.context, "begin_transaction", begin_transaction)
    monkeypatch.setattr(alembic.context, "run_migrations", lambda: None)

    with caplog.at_level(logging.INFO):
        importlib.import_module("services.api.alembic.env")

    assert "python-dotenv is not installed" in caplog.text
