"""Helper utilities for storing assistant conversation state in ``user_data``."""

from __future__ import annotations

from typing import MutableMapping, cast

from services.api.app.config import get_settings

_settings = get_settings()
ASSISTANT_MAX_TURNS: int = _settings.assistant_max_turns
ASSISTANT_SUMMARY_TRIGGER: int = _settings.assistant_summary_trigger

HISTORY_KEY = "assistant_history"
SUMMARY_KEY = "assistant_summary"
LAST_MODE_KEY = "assistant_last_mode"


def summarize(parts: list[str]) -> str:
    """Summarize *parts* into a single string.

    The default implementation simply joins messages with spaces.  Tests may
    monkeypatch this function to provide deterministic summaries.
    """
    return " ".join(parts)


def add_turn(user_data: MutableMapping[str, object], text: str) -> int:
    """Append assistant reply ``text`` to ``user_data`` keeping short history.

    When the number of stored turns reaches :data:`ASSISTANT_SUMMARY_TRIGGER`,
    older entries beyond :data:`ASSISTANT_MAX_TURNS` are summarized and the
    summary is stored under ``assistant_summary`` key.

    Returns the number of turns summarized on this call.  The return value can
    be used by higher-level services to persist summaries in a database when
    new portions are produced.
    """
    history = cast(list[str], user_data.setdefault(HISTORY_KEY, []))
    history.append(text)
    summarized = 0
    if len(history) >= ASSISTANT_SUMMARY_TRIGGER:
        old = history[:-ASSISTANT_MAX_TURNS]
        if old:
            summary = summarize(old)
            prev = cast(str | None, user_data.get(SUMMARY_KEY))
            user_data[SUMMARY_KEY] = f"{prev} {summary}".strip() if prev else summary
            summarized = len(old)
        del history[:-ASSISTANT_MAX_TURNS]
    elif len(history) > ASSISTANT_MAX_TURNS:
        del history[:-ASSISTANT_MAX_TURNS]
    return summarized


def reset(user_data: MutableMapping[str, object]) -> None:
    """Remove assistant history and summary from ``user_data``."""
    user_data.pop(HISTORY_KEY, None)
    user_data.pop(SUMMARY_KEY, None)
    user_data.pop(LAST_MODE_KEY, None)


def get_last_mode(user_data: MutableMapping[str, object]) -> str | None:
    """Return previously selected assistant mode from ``user_data``."""

    value = user_data.get(LAST_MODE_KEY)
    return cast(str | None, value) if isinstance(value, str) else None


def set_last_mode(user_data: MutableMapping[str, object], mode: str | None) -> None:
    """Persist ``mode`` in ``user_data`` or clear it when ``None``."""

    if mode is None:
        user_data.pop(LAST_MODE_KEY, None)
    else:
        user_data[LAST_MODE_KEY] = mode


__all__ = [
    "ASSISTANT_MAX_TURNS",
    "ASSISTANT_SUMMARY_TRIGGER",
    "HISTORY_KEY",
    "SUMMARY_KEY",
    "LAST_MODE_KEY",
    "summarize",
    "add_turn",
    "reset",
    "get_last_mode",
    "set_last_mode",
]
