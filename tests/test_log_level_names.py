"""Tests for standard log level name parsing."""

from __future__ import annotations

import importlib
import logging
import sys

import pytest


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("INFO", logging.INFO),
        ("warning", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("critical", logging.CRITICAL),
        ("notset", logging.NOTSET),
        ("DEBUG", logging.DEBUG),
    ],
)
def test_log_level_name_mapping(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: int
) -> None:
    """LOG_LEVEL names are mapped to logging constants."""

    monkeypatch.setenv("LOG_LEVEL", value)
    module = "services.api.app.config"
    sys.modules.pop(module, None)
    config = importlib.import_module(module)
    assert config.settings.log_level == expected
