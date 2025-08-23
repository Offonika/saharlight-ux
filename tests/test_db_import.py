from __future__ import annotations

import logging
import sys
import types

import pytest

from services.api.app.diabetes.utils.db_import import get_run_db


def test_get_run_db_success() -> None:
    assert get_run_db() is not None


def test_get_run_db_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    dummy = types.ModuleType("services.api.app.diabetes.services.db")
    monkeypatch.setitem(sys.modules, "services.api.app.diabetes.services.db", dummy)
    with caplog.at_level(logging.ERROR):
        assert get_run_db() is None
    assert "Unexpected error importing run_db" in caplog.text
