from types import ModuleType

import importlib
import sys
from typing import Any, ContextManager, cast

import pytest


def _reload(module: str) -> ModuleType:
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


class DummyEngine:
    def __init__(self, url: Any) -> None:
        self.url = url
        self.disposed = False

    def dispose(self) -> None:
        self.disposed = True

    def begin(self) -> ContextManager["DummyEngine"]:  # type: ignore[override]
        class _Ctx(ContextManager["DummyEngine"]):
            def __enter__(self_inner) -> "DummyEngine":
                return self

            def __exit__(self_inner, *args: object) -> None:
                return None

        return _Ctx()


@pytest.mark.parametrize(
    ("attr", "orig", "new", "url_attr"),
    [
        ("db_host", "host1", "host2", "host"),
        ("db_name", "name1", "name2", "database"),
    ],
)
def test_init_db_recreates_engine_on_url_change(
    monkeypatch: pytest.MonkeyPatch, attr: Any, orig: Any, new: Any, url_attr: Any
) -> None:
    monkeypatch.setenv("DB_PASSWORD", "pwd")
    _reload("services.api.app.config")
    db = cast(Any, _reload("services.api.app.diabetes.services.db"))

    created: list[DummyEngine] = []

    def fake_create_engine(url: Any) -> DummyEngine:
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
