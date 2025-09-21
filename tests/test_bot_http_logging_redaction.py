"""Ensure HTTP client logs mask Telegram bot tokens."""

from __future__ import annotations

import logging

import pytest

from services.bot import main as bot_main


def test_http_client_logs_redact_token(caplog: pytest.LogCaptureFixture) -> None:
    """httpx logs should not expose the raw Telegram token."""

    token = "123456:ABCDEF"
    root_logger = logging.getLogger()
    original_root_level = root_logger.level
    original_root_filters = root_logger.filters[:]
    original_levels = {
        name: logging.getLogger(name).level
        for name in bot_main.HTTP_CLIENT_LOGGER_NAMES
    }
    original_filters = {
        name: logging.getLogger(name).filters[:]
        for name in bot_main.HTTP_CLIENT_LOGGER_NAMES
    }

    try:
        bot_main.configure_http_client_logging(token)
        http_logger = logging.getLogger("httpx")
        with caplog.at_level(logging.INFO, logger="httpx"):
            http_logger.info(
                "POST https://api.telegram.org/bot%s/sendMessage", token
            )
    finally:
        root_logger.setLevel(original_root_level)
        root_logger.filters[:] = original_root_filters
        for name in bot_main.HTTP_CLIENT_LOGGER_NAMES:
            logger_instance = logging.getLogger(name)
            logger_instance.setLevel(original_levels[name])
            logger_instance.filters[:] = original_filters[name]

    assert caplog.records, "Expected httpx log entry to be captured"
    messages = [record.getMessage() for record in caplog.records]
    assert all(f"bot{token}" not in message for message in messages)
    assert any(
        bot_main.TELEGRAM_TOKEN_PLACEHOLDER in message for message in messages
    )
