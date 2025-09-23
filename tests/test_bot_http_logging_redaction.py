"""Ensure HTTP client logs mask Telegram bot tokens."""

from __future__ import annotations

import logging
from collections.abc import Iterable

import pytest

from services.bot import main as bot_main


def _collect_logger_names_with_children(base_names: Iterable[str]) -> set[str]:
    names = set(base_names)
    logger_dict = logging.Logger.manager.loggerDict
    for base_name in base_names:
        prefix = f"{base_name}."
        for candidate, logger_obj in list(logger_dict.items()):
            if (
                isinstance(logger_obj, logging.Logger)
                and candidate.startswith(prefix)
            ):
                names.add(candidate)
    return names


def _snapshot_logger_state(logger_names: Iterable[str]) -> dict[str, tuple[int, list[logging.Filter]]]:
    snapshot: dict[str, tuple[int, list[logging.Filter]]] = {}
    for name in logger_names:
        logger_instance = logging.getLogger(name)
        snapshot[name] = (logger_instance.level, logger_instance.filters[:])
    return snapshot


def _restore_logger_state(snapshot: dict[str, tuple[int, list[logging.Filter]]]) -> None:
    for name, (level, filters) in snapshot.items():
        logger_instance = logging.getLogger(name)
        logger_instance.setLevel(level)
        logger_instance.filters[:] = filters


def test_http_client_logs_redact_token(caplog: pytest.LogCaptureFixture) -> None:
    """httpx logs should not expose the raw Telegram token."""

    token = "123456:ABCDEF"
    root_logger = logging.getLogger()
    original_root_level = root_logger.level
    original_root_filters = root_logger.filters[:]
    tracked_loggers = _collect_logger_names_with_children(
        bot_main.HTTP_CLIENT_LOGGER_NAMES
    )
    tracked_loggers.add("telegram.ext.ExtBot")
    original_state = _snapshot_logger_state(tracked_loggers)

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
        _restore_logger_state(original_state)

    assert caplog.records, "Expected httpx log entry to be captured"
    messages = [record.getMessage() for record in caplog.records]
    assert all(f"bot{token}" not in message for message in messages)
    assert any(
        bot_main.TELEGRAM_TOKEN_PLACEHOLDER in message for message in messages
    )


def test_telegram_ext_logs_redact_token(caplog: pytest.LogCaptureFixture) -> None:
    """telegram.ext debug logs must replace bot tokens with placeholder."""

    token = "777777:SECRET"
    root_logger = logging.getLogger()
    original_root_level = root_logger.level
    original_root_filters = root_logger.filters[:]
    tracked_loggers = _collect_logger_names_with_children(
        bot_main.HTTP_CLIENT_LOGGER_NAMES
    )
    tracked_loggers.add("telegram.ext.ExtBot")
    original_state = _snapshot_logger_state(tracked_loggers)

    try:
        bot_main.configure_http_client_logging(token)
        ext_logger = logging.getLogger("telegram.ext.ExtBot")
        with caplog.at_level(logging.DEBUG, logger="telegram.ext.ExtBot"):
            ext_logger.debug(
                "GET https://api.telegram.org/bot%s/getMe", token
            )
    finally:
        root_logger.setLevel(original_root_level)
        root_logger.filters[:] = original_root_filters
        _restore_logger_state(original_state)

    assert caplog.records, "Expected telegram.ext.ExtBot log entry to be captured"
    messages = [record.getMessage() for record in caplog.records]
    assert all(f"bot{token}" not in message for message in messages)
    assert any(
        bot_main.TELEGRAM_TOKEN_PLACEHOLDER in message for message in messages
    )
