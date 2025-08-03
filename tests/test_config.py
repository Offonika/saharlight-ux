# test_config.py

import importlib
import sys

import pytest


def test_empty_db_password_raises(monkeypatch):
    monkeypatch.setenv('DB_PASSWORD', '')
    if 'diabetes.config' in sys.modules:
        del sys.modules['diabetes.config']
    with pytest.raises(ValueError):
        importlib.import_module('diabetes.config')
    if 'diabetes.config' in sys.modules:
        del sys.modules['diabetes.config']
