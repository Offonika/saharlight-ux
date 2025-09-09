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
    dia: float | None = None,
    iob: float | None = None,
) -> float:
    """Calculate bolus based on carbohydrates and blood glucose.

    Args:
        carbs: Amount of carbohydrates either in grams or XE units.
        current_bg: Current blood glucose level.
        profile: Patient profile with calculation coefficients.
        carb_units: Unit of ``carbs`` – grams (``"g"``) or XE (``"xe"``).
        bolus_round_step: Step size for floor rounding of the result.
        max_bolus: Optional maximum bolus allowed. ``None`` disables capping.
        dia: Duration of insulin action in hours. Influences the impact of ``iob``.
        iob: Insulin on board to subtract from the recommendation.

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

    if iob is not None:
        if iob < 0:
            raise ValueError("iob must be non-negative")
        effective_iob = Decimal(str(iob))
        if dia is not None:
            if dia <= 0:
                raise ValueError("dia must be greater than 0")
            effective_iob *= Decimal("4") / Decimal(str(dia))
        total -= effective_iob
        if total < 0:
            total = Decimal("0")

    total_f = float(total)
    if max_bolus is not None:
        if max_bolus < 0:
            raise ValueError("max_bolus must be non-negative")
        total_f = min(total_f, max_bolus)

    return _round_bolus(total_f, bolus_round_step)


__all__ = ["PatientProfile", "_round_bolus", "calc_bolus"]
