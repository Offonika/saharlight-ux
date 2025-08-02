# functions.py

from dataclasses import dataclass
import re


@dataclass
class PatientProfile:
    icr: float
    cf: float
    target_bg: float


def calc_bolus(carbs_g: float, current_bg: float, profile: PatientProfile) -> float:
    """
    Расчёт болюса (дозы инсулина) по углеводам и сахару.
    """
    if profile.icr <= 0:
        raise ValueError("Profile icr must be greater than 0")
    if profile.cf <= 0:
        raise ValueError("Profile cf must be greater than 0")
    if carbs_g < 0:
        raise ValueError("carbs_g must be non-negative")
    if current_bg < 0:
        raise ValueError("current_bg must be non-negative")
    meal = carbs_g / profile.icr
    correction = max(0, (current_bg - profile.target_bg) / profile.cf)
    return round(meal + correction, 1)


def extract_nutrition_info(text: str):
    carbs = xe = None
    # Парсим углеводы (carbs)
    m = re.search(r"углевод[^\d]*:\s*([\d.,]+)\s*г", text, re.IGNORECASE)
    if m:
        carbs = float(m.group(1).replace(",", "."))
    # Диапазон XE c двоеточием (например XE: 2–3)
    rng = re.search(r"\b(?:[хx][еe]|xe)\s*:\s*(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)", text, re.IGNORECASE)
    if rng:
        xe = (float(rng.group(1).replace(",", ".")) +
              float(rng.group(2).replace(",", "."))) / 2
    else:
        # Одинарное значение XE: 3.1
        m = re.search(r"\b(?:[хx][еe]|xe)\s*:\s*([\d.,]+)", text, re.IGNORECASE)
        if m:
            xe = float(m.group(1).replace(",", "."))
        # Диапазон XE без двоеточия (например 2–3 ХЕ)
        if xe is None:
            rng = re.search(r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*(?:[хx][еe]|xe)", text, re.IGNORECASE)
            if rng:
                xe = (float(rng.group(1).replace(",", ".")) +
                      float(rng.group(2).replace(",", "."))) / 2
    # Диапазон углеводов (carbs) если не найдено
    if carbs is None:
        rng = re.search(r"(\d+[.,]?\d*)\s*[–-]\s*(\d+[.,]?\d*)\s*г", text, re.IGNORECASE)
        if rng:
            carbs = (float(rng.group(1).replace(",", ".")) +
                     float(rng.group(2).replace(",", "."))) / 2
    return carbs, xe
