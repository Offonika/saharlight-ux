from __future__ import annotations

import logging

import pytest

from services.api.app.diabetes.handlers import dose_calc
from services.api.app.diabetes.handlers.dose_validation import _sanitize


def test_sanitize_removes_control_chars_and_truncates() -> None:
    text = "abc" + chr(0) + "def\n" + "x" * 50
    assert _sanitize(text, max_len=10) == "abcdefxxxx"


def test_logging_truncates_content(caplog: pytest.LogCaptureFixture) -> None:
    long_text = "A" * 250 + "\x00\x01"
    with caplog.at_level(logging.DEBUG):
        dose_calc.logger.debug("test %s", _sanitize(long_text))
    record = caplog.records[0]
    assert "A" * 200 in record.message
    assert "A" * 201 not in record.message
    assert "\x00" not in record.message
    assert "\x01" not in record.message
