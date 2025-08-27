import logging

import pytest

from services.api.app.diabetes.handlers.dose_handlers import logger, _sanitize


def test_logging_truncates_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    long_text = "A" * 250 + "\x00\x01"
    with caplog.at_level(logging.DEBUG):
        logger.debug("test %s", _sanitize(long_text))
    record = caplog.records[0]
    assert "A" * 200 in record.message
    assert "A" * 201 not in record.message
    assert "\x00" not in record.message
    assert "\x01" not in record.message
