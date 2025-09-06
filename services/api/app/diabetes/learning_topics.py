from __future__ import annotations

from typing import Mapping


def choose_initial_topic(profile: Mapping[str, str | None]) -> str:
    """Return the initial topic slug based on a user's profile.

    - Novice users on insulin therapy start with ``xe_basics``.
    - Novice users on non-insulin therapy start with ``healthy-eating``.
    - Users with intermediate or advanced knowledge start with ``basics-of-diabetes``.
    """

    level = (profile.get("learning_level") or "").lower()
    therapy = (profile.get("therapy_type") or "").lower()

    if level != "novice":
        return "basics-of-diabetes"
    if therapy in {"insulin", "mixed"}:
        return "xe_basics"
    return "healthy-eating"


__all__ = ["choose_initial_topic"]
