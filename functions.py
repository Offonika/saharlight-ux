# functions.py
from dataclasses import dataclass

@dataclass
class PatientProfile:
    icr: float
    cf: float
    target_bg: float

def calc_bolus(carbs_g: float, current_bg: float, profile: PatientProfile) -> float:
    meal = carbs_g / profile.icr
    correction = max(0, (current_bg - profile.target_bg) / profile.cf)
    return round(meal + correction, 1)
