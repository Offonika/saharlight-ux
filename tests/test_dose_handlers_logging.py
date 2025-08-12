import logging

from apps.telegram_bot import dose_handlers


def test_logging_truncates_content(caplog):
    long_text = "A" * 250 + "\x00\x01"
    with caplog.at_level(logging.DEBUG):
        dose_handlers.logger.debug("test %s", dose_handlers._sanitize(long_text))
    record = caplog.records[0]
    assert "A" * 200 in record.message
    assert "A" * 201 not in record.message
    assert "\x00" not in record.message
    assert "\x01" not in record.message
