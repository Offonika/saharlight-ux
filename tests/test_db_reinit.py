import importlib
import sys

import pytest


def _reload(module: str):
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


class DummyEngine:
    def __init__(self, url):
        self.url = url
        self.disposed = False

    def dispose(self):
        self.disposed = True


@pytest.mark.parametrize(
    ("attr", "orig", "new", "url_attr"),
    [
        ("db_host", "host1", "host2", "host"),
        ("db_name", "name1", "name2", "database"),
    ],
)

def test_init_db_recreates_engine_on_url_change(monkeypatch, attr, orig, new, url_attr):
    monkeypatch.setenv("DB_PASSWORD", "pwd")
    _reload("services.api.app.config")
    db = _reload("services.api.app.diabetes.services.db")

    created = []

    def fake_create_engine(url):
        engine = DummyEngine(url)
        created.append(engine)
        return engine

    monkeypatch.setattr(db, "create_engine", fake_create_engine)
    monkeypatch.setattr(db.Base.metadata, "create_all", lambda bind: None)

    monkeypatch.setattr(db.settings, attr, orig)
    db.engine = None
    db.init_db()
    first_engine = db.engine
    assert getattr(first_engine.url, url_attr) == orig

    monkeypatch.setattr(db.settings, attr, new)
    db.init_db()
    second_engine = db.engine

    assert first_engine.disposed is True
    assert second_engine is not first_engine
    assert getattr(second_engine.url, url_attr) == new
