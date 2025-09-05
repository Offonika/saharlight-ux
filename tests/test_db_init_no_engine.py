import importlib
import sys
from types import ModuleType
from typing import Any, cast

import pytest


def _reload(module: str) -> ModuleType:
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


def test_init_db_raises_when_engine_not_created(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PASSWORD", "pwd")
    _reload("services.api.app.config")
    db = cast(Any, _reload("services.api.app.diabetes.services.db"))

    monkeypatch.setattr(db, "create_engine", lambda url: None)

    with pytest.raises(RuntimeError):
        db.init_db()
    db.init_db = lambda: None
