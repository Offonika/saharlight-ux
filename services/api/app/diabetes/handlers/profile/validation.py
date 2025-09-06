from __future__ import annotations

"""Utilities for parsing and validating user input for profile handlers."""

from collections.abc import Mapping
from typing import Any


# User-facing validation messages reused across conversation flows.
MSG_ICR_GT0 = "ИКХ должен быть больше 0."
MSG_CF_GT0 = "КЧ должен быть больше 0."
MSG_TARGET_GT0 = "Целевой сахар должен быть больше 0."
MSG_LOW_GT0 = "Нижний порог должен быть больше 0."
MSG_HIGH_GT_LOW = "Верхний порог должен быть больше нижнего и больше 0."
MSG_TARGET_RANGE = "Целевой сахар должен быть между нижним и верхним порогами."


def parse_profile_args(args: list[str]) -> dict[str, str] | None:
    """Parse ``/profile`` command arguments into a dict."""
    if len(args) == 5 and all("=" not in a for a in args):
        return {
            "icr": args[0],
            "cf": args[1],
            "target": args[2],
            "low": args[3],
            "high": args[4],
        }

    parsed: dict[str, str] = {}
    for arg in args:
        if "=" not in arg:
            return None
        key, val = arg.split("=", 1)
        key = key.lower()
        match = None
        for full in ("icr", "cf", "target", "low", "high"):
            if full.startswith(key):
                match = full
                break
        if not match:
            return None
        parsed[match] = val
    if set(parsed) == {"icr", "cf", "target", "low", "high"}:
        return parsed
    return None


def validate_profile_numbers(
    icr: float, cf: float, target: float, low: float, high: float
) -> str | None:
    """Validate numeric profile parameters.

    Returns an error message if validation fails, otherwise ``None``.
    """

    if icr <= 0:
        return MSG_ICR_GT0
    if cf <= 0:
        return MSG_CF_GT0
    if target <= 0:
        return MSG_TARGET_GT0
    if low <= 0:
        return MSG_LOW_GT0
    if high <= low:
        return MSG_HIGH_GT_LOW
    if not (low < target < high):
        return MSG_TARGET_RANGE
    return None


def parse_profile_values(
    values: Mapping[str, Any],
) -> tuple[float, float, float, float, float]:
    """Convert mapping of strings to floats and validate profile numbers.

    Raises :class:`ValueError` if conversion fails or if the numbers fail
    :func:`validate_profile_numbers` checks.  When validation fails the error
    message from :func:`validate_profile_numbers` is attached to the exception.
    """

    try:
        icr = float(str(values["icr"]).replace(",", "."))
        cf = float(str(values["cf"]).replace(",", "."))
        target = float(str(values["target"]).replace(",", "."))
        low = float(str(values["low"]).replace(",", "."))
        high = float(str(values["high"]).replace(",", "."))
    except (KeyError, ValueError) as exc:  # pragma: no cover - exact message unused
        raise ValueError from exc

    error = validate_profile_numbers(icr, cf, target, low, high)
    if error:
        raise ValueError(error)
    return icr, cf, target, low, high
