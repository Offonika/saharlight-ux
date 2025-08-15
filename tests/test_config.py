# test_config.py

import importlib
import sys
from types import ModuleType

import pytest


def _reload(module: str) -> ModuleType:
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


def test_import_config_without_db_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    _reload("services.api.app.config")  # should not raise


def test_init_db_raises_when_no_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    config = _reload("services.api.app.config")
    db = _reload("services.api.app.diabetes.services.db")
    assert config.get_db_password() is None
    with pytest.raises(ValueError):
        db.init_db()
