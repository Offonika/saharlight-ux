from __future__ import annotations

import builtins
from typing import Any

import pytest

from services.api.app.diabetes.utils.db_import import get_run_db


def test_get_run_db_success() -> None:
    run_db = get_run_db()
    assert run_db is not None


def test_get_run_db_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "services.api.app.diabetes.services.db":
            raise ImportError
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert get_run_db() is None


def test_get_run_db_other_error(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "services.api.app.diabetes.services.db":
            raise RuntimeError("boom")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert get_run_db() is None
