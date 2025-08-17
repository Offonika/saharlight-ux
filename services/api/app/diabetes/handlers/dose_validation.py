"""Validation utilities for dose handlers."""

from __future__ import annotations

import re


def _sanitize(text: str, max_len: int = 200) -> str:
    """Strip control chars and truncate for safe logging."""
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(text))
    return cleaned[:max_len]


__all__ = ["_sanitize"]
