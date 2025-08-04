# test_config.py

import importlib
import sys

import pytest


def _reload(module: str):
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


def test_import_config_without_db_password(monkeypatch):
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    _reload("diabetes.config")  # should not raise


def test_init_db_raises_when_no_password(monkeypatch):
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    _reload("diabetes.config")
    db = _reload("diabetes.db")
    with pytest.raises(ValueError):
        db.init_db()

