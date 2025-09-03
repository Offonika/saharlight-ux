from __future__ import annotations

import hashlib
import os
from typing import Sequence


def choose_variant(user_id: int, variants: Sequence[str] = ("A", "B")) -> str:
    """Return deterministic A/B variant for ``user_id``.

    Variant is stable for the same ``user_id`` and split 50/50 across
    ``variants`` using a hash. The experiment can be disabled by setting
    the environment variable ``ONBOARDING_AB" to ``"0"`` or ``"false"``.
    In that case the first variant is always returned.
    """
    flag = os.getenv("ONBOARDING_AB", "1").lower()
    if flag in {"0", "false", "off"}:
        return variants[0]
    digest = hashlib.blake2b(str(user_id).encode(), digest_size=2).digest()
    idx = int.from_bytes(digest, "big") % len(variants)
    return variants[idx]


__all__ = ["choose_variant"]
