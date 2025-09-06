"""Miscellaneous utilities for the learning module."""

from __future__ import annotations

from typing import Mapping

NOVICE_LEVELS = {"novice", "beginner", "a"}
INSULIN_THERAPIES = {"insulin", "mixed"}

__all__ = ["choose_initial_topic"]


def choose_initial_topic(profile: Mapping[str, str | None]) -> tuple[str, str]:
    """Choose an initial learning topic based on ``profile``.

    For novices with insulin therapy the user learns about insulin usage first.
    Novices on non-insulin therapy start with diabetes basics. Non-novices are
    directed to carbohydrate counting for insulin therapy and healthy eating for
    non-insulin therapy.
    """

    level = str(profile.get("learning_level", "novice")).lower()
    therapy = str(
        profile.get("therapyType") or profile.get("therapy_type") or "insulin"
    ).lower()

    is_novice = level in NOVICE_LEVELS
    is_insulin = therapy in INSULIN_THERAPIES

    if is_novice:
        return (
            ("insulin-usage", "Инсулин")
            if is_insulin
            else ("basics-of-diabetes", "Основы диабета")
        )
    return (
        ("xe_basics", "Хлебные единицы")
        if is_insulin
        else ("healthy-eating", "Здоровое питание")
    )
