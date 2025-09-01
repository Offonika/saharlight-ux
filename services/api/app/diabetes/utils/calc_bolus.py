"""Utilities for calculating insulin bolus."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, localcontext
from typing import Literal

from .constants import XE_GRAMS


@dataclass
class PatientProfile:
    """Patient-specific coefficients for bolus calculation.

    Attributes:
        icr: Insulin-to-carb ratio (grams of carbs covered by 1 unit).
        cf: Correction factor for lowering blood glucose by 1 unit.
        target_bg: Target blood glucose level.
    """

    icr: float
    cf: float
    target_bg: float


def _round_bolus(value: float, step: float) -> float:
    """Round ``value`` down to the nearest ``step``.

    Args:
        value: Unrounded bolus value.
        step: Rounding step in insulin units. Must be positive.

    Returns:
        ``value`` rounded down to the nearest multiple of ``step``.
    """
    if step <= 0:
        raise ValueError("bolus_round_step must be positive")
    with localcontext() as ctx:
        ctx.prec = 6
        v = Decimal(str(value))
        s = Decimal(str(step))
        rounded = (v / s).to_integral_value(rounding=ROUND_FLOOR) * s
        return float(rounded)


def calc_bolus(
    carbs: float,
    current_bg: float,
    profile: PatientProfile,
    *,
    carb_units: Literal["g", "xe"] = "g",
    bolus_round_step: float = 0.5,
    max_bolus: float | None = None,
    dia: float | None = None,  # pragma: no cover - placeholder
    iob: float | None = None,  # pragma: no cover - placeholder
) -> float:
    """Calculate bolus based on carbohydrates and blood glucose.

    Args:
        carbs: Amount of carbohydrates either in grams or XE units.
        current_bg: Current blood glucose level.
        profile: Patient profile with calculation coefficients.
        carb_units: Unit of ``carbs`` – grams (``"g"``) or XE (``"xe"``).
        bolus_round_step: Step size for floor rounding of the result.
        max_bolus: Optional maximum bolus allowed. ``None`` disables capping.
        dia: Duration of insulin action (not used yet).
        iob: Insulin on board (not used yet).

    Returns:
        Rounded bolus value in insulin units.
    """
    if profile.icr <= 0:
        raise ValueError("Profile icr must be greater than 0")
    if profile.cf <= 0:
        raise ValueError("Profile cf must be greater than 0")
    if profile.target_bg <= 0:
        raise ValueError("Profile target_bg must be greater than 0")
    if carbs < 0:
        raise ValueError("carbs must be non-negative")
    if current_bg < 0:
        raise ValueError("current_bg must be non-negative")
    if bolus_round_step <= 0:
        raise ValueError("bolus_round_step must be positive")

    if carb_units == "xe":
        carbs_g = carbs * XE_GRAMS
    elif carb_units == "g":
        carbs_g = carbs
    else:  # pragma: no cover - invalid unit branch
        raise ValueError("carb_units must be 'g' or 'xe'")

    with localcontext() as ctx:
        ctx.prec = 6
        carbs_d = Decimal(str(carbs_g))
        icr_d = Decimal(str(profile.icr))
        cf_d = Decimal(str(profile.cf))
        target_d = Decimal(str(profile.target_bg))
        current_d = Decimal(str(current_bg))
        meal = carbs_d / icr_d
        correction = (current_d - target_d) / cf_d
        if correction < 0:
            correction = Decimal("0")
        total = meal + correction

    total_f = float(total)
    if max_bolus is not None:
        total_f = min(total_f, max_bolus)

    return _round_bolus(total_f, bolus_round_step)


__all__ = ["PatientProfile", "_round_bolus", "calc_bolus"]
