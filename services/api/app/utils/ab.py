"""A/B testing utilities."""

from __future__ import annotations

import hashlib
from typing import Sequence


def choose_variant(user_id: int, variants: Sequence[str] = ("A", "B")) -> str:
    """Deterministically choose a variant for ``user_id``.

    Parameters
    ----------
    user_id: int
        Telegram user identifier used for hashing.
    variants: Sequence[str]
        Available variants to choose from. Defaults to ("A", "B").

    Returns
    -------
    str
        Selected variant name.
    """
    if not variants:
        raise ValueError("variants must be non-empty")
    digest = hashlib.sha256(str(user_id).encode("utf-8")).digest()
    idx = int.from_bytes(digest[:4], "big") % len(variants)
    return variants[idx]
