"""Helper utilities for storing assistant conversation state in ``user_data``."""

from __future__ import annotations

from typing import MutableMapping, cast

ASSISTANT_MAX_TURNS: int = 20
ASSISTANT_SUMMARY_TRIGGER: int = 40

HISTORY_KEY = "assistant_history"
SUMMARY_KEY = "assistant_summary"


def summarize(parts: list[str]) -> str:
    """Summarize *parts* into a single string.

    The default implementation simply joins messages with spaces.  Tests may
    monkeypatch this function to provide deterministic summaries.
    """
    return " ".join(parts)


def add_turn(user_data: MutableMapping[str, object], text: str) -> str | None:
    """Append assistant reply ``text`` to ``user_data`` keeping short history.

    When the number of stored turns reaches :data:`ASSISTANT_SUMMARY_TRIGGER`,
    older entries beyond :data:`ASSISTANT_MAX_TURNS` are summarized and the
    summary is stored under ``assistant_summary`` key.

    Returns the updated summary when one was generated, otherwise ``None``.
    """
    history = cast(list[str], user_data.setdefault(HISTORY_KEY, []))
    history.append(text)
    summary: str | None = None
    if len(history) >= ASSISTANT_SUMMARY_TRIGGER:
        old = history[:-ASSISTANT_MAX_TURNS]
        if old:
            summary = summarize(old)
            prev = cast(str | None, user_data.get(SUMMARY_KEY))
            user_data[SUMMARY_KEY] = f"{prev} {summary}".strip() if prev else summary
        del history[:-ASSISTANT_MAX_TURNS]
    elif len(history) > ASSISTANT_MAX_TURNS:
        del history[:-ASSISTANT_MAX_TURNS]
    return summary


def reset(user_data: MutableMapping[str, object]) -> None:
    """Remove assistant history and summary from ``user_data``."""
    user_data.pop(HISTORY_KEY, None)
    user_data.pop(SUMMARY_KEY, None)


__all__ = [
    "ASSISTANT_MAX_TURNS",
    "ASSISTANT_SUMMARY_TRIGGER",
    "HISTORY_KEY",
    "SUMMARY_KEY",
    "summarize",
    "add_turn",
    "reset",
]
