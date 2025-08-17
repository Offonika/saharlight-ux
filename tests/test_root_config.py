"""Tests for the top-level :mod:`config` module."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest


def _reload(module: str) -> ModuleType:
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


def test_validate_tokens_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expect ``RuntimeError`` when a required variable is absent."""

    monkeypatch.delenv("UNDECLARED_TOKEN", raising=False)
    config = _reload("config")

    with pytest.raises(RuntimeError):
        config.validate_tokens(["UNDECLARED_TOKEN"])


def test_validate_tokens_env_not_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    """Variables set in the environment but not exposed are still validated."""

    monkeypatch.setenv("UNDECLARED_TOKEN", "secret")
    config = _reload("config")

    assert not hasattr(config, "UNDECLARED_TOKEN")

    config.validate_tokens(["UNDECLARED_TOKEN"])
