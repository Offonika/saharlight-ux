# test_config.py

import importlib
import sys

import pytest
import logging


def _reload(module: str):
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


def test_import_config_without_db_password(monkeypatch):
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    _reload("backend.config")  # should not raise


def test_init_db_raises_when_no_password(monkeypatch):
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.setenv("SKIP_DOTENV", "1")
    config = _reload("backend.config")
    db = _reload("diabetes.db")
    assert config.DB_PASSWORD is None
    with pytest.raises(ValueError):
        db.init_db()


def test_webapp_url_missing(monkeypatch, caplog):
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    monkeypatch.setenv("SKIP_DOTENV", "1")
    with caplog.at_level(logging.WARNING):
        config = _reload("backend.config")
    assert config.WEBAPP_URL is None
    assert any("WEBAPP_URL is not set" in msg for msg in caplog.messages)


def test_webapp_url_requires_https(monkeypatch, caplog):
    monkeypatch.setenv("WEBAPP_URL", "http://example.com")
    monkeypatch.setenv("SKIP_DOTENV", "1")
    with caplog.at_level(logging.WARNING):
        config = _reload("backend.config")
    assert config.WEBAPP_URL is None
    assert any("Ignoring WEBAPP_URL" in msg and "not HTTPS" in msg for msg in caplog.messages)


def test_webapp_url_valid(monkeypatch, caplog):
    url = "https://example.com"
    monkeypatch.setenv("WEBAPP_URL", url)
    monkeypatch.setenv("SKIP_DOTENV", "1")
    with caplog.at_level(logging.WARNING):
        config = _reload("backend.config")
    assert config.WEBAPP_URL == url
    assert not caplog.messages

