"""Tests for legacy lessons loading."""

from __future__ import annotations

import importlib
import json
import logging
from typing import NoReturn, TextIO

import pytest


def test_lessons_v0_load_logs_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure logger captures errors during legacy lessons load."""

    import services.api.app.diabetes.prompts as prompts

    def bad_json_load(_fp: TextIO) -> NoReturn:
        raise json.JSONDecodeError("bad", "", 0)

    monkeypatch.setattr(json, "load", bad_json_load)

    with caplog.at_level(logging.ERROR):
        importlib.reload(prompts)

    assert "Failed to load legacy lessons" in caplog.text
    assert prompts.LESSONS_V0_DATA == {}

    monkeypatch.undo()
    importlib.reload(prompts)
