"""Utilities for generating and formatting learning plans.

The planner is intentionally simple: it picks a sequence of topic slugs
depending on user's profile and exposes helpers to present the plan to a
human.  It does **not** access the database and therefore is easily
unit-testable.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from services.api.app.config import TOPICS_RU

# Order of topics for a novice user.  Advanced users skip the first item –
# basic theory of diabetes – and start straight with practical topics.
DEFAULT_PLAN: list[str] = [
    "basics-of-diabetes",
    "xe_basics",
    "healthy-eating",
    "insulin-usage",
]


def generate_learning_plan(profile: Mapping[str, object]) -> list[str]:
    """Return a list of topic slugs forming a learning plan.

    Parameters
    ----------
    profile:
        Mapping of profile attributes.  Only ``learning_level`` is used at the
        moment, other keys are ignored.  The function never mutates ``profile``.

    The function currently supports two learning levels:

    ``novice``
        Full :data:`DEFAULT_PLAN`.

    anything else
        The first introductory topic is skipped.
    """

    level = str(profile.get("learning_level", "novice") or "novice").lower()
    if level == "novice":
        return list(DEFAULT_PLAN)
    return list(DEFAULT_PLAN[1:])


def pretty_plan(plan: Sequence[str], current: int) -> str:
    """Return a human friendly representation of ``plan``.

    ``current`` is a zero-based index of the active step.  The current item is
    highlighted with an arrow emoji.  Unknown slugs are returned as-is.
    """

    lines: list[str] = []
    for idx, slug in enumerate(plan, start=1):
        title = TOPICS_RU.get(slug, slug)
        prefix = "👉 " if idx - 1 == current else ""
        lines.append(f"{idx}. {prefix}{title}")
    return "\n".join(lines)


__all__ = ["generate_learning_plan", "pretty_plan", "DEFAULT_PLAN"]
