"""Utilities for building and formatting learning plans."""
from __future__ import annotations

from typing import Sequence


def generate_learning_plan(first_step: str | None = None) -> list[str]:
    """Generate a basic learning plan.

    Parameters
    ----------
    first_step:
        Optional text for the first plan step.
    """

    return [
        first_step or "Шаг 1: основы диабета",
        "Шаг 2: контроль питания",
        "Шаг 3: мониторинг сахара",
    ]


def pretty_plan(plan: Sequence[str]) -> str:
    """Return a human friendly representation of *plan*."""

    return "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
