# functions.py
from dataclasses import dataclass


@dataclass
class PatientProfile:
    icr: float
    cf: float
    target_bg: float


def calc_bolus(carbs_g: float, current_bg: float, profile: PatientProfile) -> float:
    """Calculate insulin bolus for a meal.

    Args:
        carbs_g: Amount of carbohydrates in grams.
        current_bg: Current blood glucose level.
        profile: Patient parameters with insulin-to-carb ratio (icr),
            correction factor (cf) and target blood glucose.

    Returns:
        Recommended bolus rounded to one decimal place.

    Raises:
        ValueError: If ``profile.icr`` or ``profile.cf`` are not positive,
            or ``carbs_g`` or ``current_bg`` are negative.
    """

    if profile.icr <= 0 or profile.cf <= 0:
        raise ValueError("icr and cf must be positive values")

    if carbs_g < 0 or current_bg < 0:
        raise ValueError("carbs_g and current_bg must be non-negative values")

    meal = carbs_g / profile.icr
    correction = max(0, (current_bg - profile.target_bg) / profile.cf)
    return round(meal + correction, 1)
