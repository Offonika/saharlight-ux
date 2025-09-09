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


def test_validate_tokens_reload_settings_on_any_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any required variable triggers a settings reload."""

    monkeypatch.setenv("UNDECLARED_TOKEN", "secret")
    config = _reload("config")

    called = False

    def fake_reload_settings() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(config, "reload_settings", fake_reload_settings)

    config.validate_tokens(["UNDECLARED_TOKEN"])

    assert called


def test_validate_tokens_reflects_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """``validate_tokens`` checks the current ``TELEGRAM_TOKEN`` value."""

    monkeypatch.setenv("TELEGRAM_TOKEN", "initial")
    config = _reload("config")
    config.validate_tokens(["TELEGRAM_TOKEN"])

    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        config.validate_tokens(["TELEGRAM_TOKEN"])

    monkeypatch.setenv("TELEGRAM_TOKEN", "updated")
    config.validate_tokens(["TELEGRAM_TOKEN"])


def test_validate_tokens_missing_telegram_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting ``TELEGRAM_TOKEN`` causes validation to fail."""

    monkeypatch.setenv("TELEGRAM_TOKEN", "present")
    config = _reload("config")
    config.validate_tokens(["TELEGRAM_TOKEN"])

    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        config.validate_tokens(["TELEGRAM_TOKEN"])
