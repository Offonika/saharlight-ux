import pytest

from services.api.app.diabetes.utils.calc_bolus import (
    PatientProfile,
    calc_bolus,
)
from services.api.app.diabetes.utils.constants import XE_GRAMS


def test_calc_bolus_xe_vs_grams() -> None:
    profile = PatientProfile(icr=12, cf=2, target_bg=6)
    dose_xe = calc_bolus(
        carbs=5,
        current_bg=8,
        profile=profile,
        carb_units="xe",
        bolus_round_step=0.1,
    )
    dose_g = calc_bolus(
        carbs=5 * XE_GRAMS,
        current_bg=8,
        profile=profile,
        carb_units="g",
        bolus_round_step=0.1,
    )
    assert dose_xe == dose_g


def test_calc_bolus_rounding_step() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    # meal = 43/10=4.3, correction=(8-6)/2=1 -> 5.3
    dose = calc_bolus(
        carbs=43,
        current_bg=8,
        profile=profile,
        bolus_round_step=0.5,
    )
    assert dose == 5.0
    dose_precise = calc_bolus(
        carbs=43,
        current_bg=8,
        profile=profile,
        bolus_round_step=0.1,
    )
    assert dose_precise == pytest.approx(5.3)


def test_calc_bolus_max_limit() -> None:
    profile = PatientProfile(icr=5, cf=1, target_bg=5)
    dose = calc_bolus(
        carbs=100,
        current_bg=12,
        profile=profile,
        bolus_round_step=0.5,
        max_bolus=6.0,
    )
    assert dose == 6.0


def test_calc_bolus_iob_and_dia() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    dose_no_iob = calc_bolus(
        carbs=50,
        current_bg=8,
        profile=profile,
        bolus_round_step=0.1,
    )
    dose_with_iob = calc_bolus(
        carbs=50,
        current_bg=8,
        profile=profile,
        bolus_round_step=0.1,
        iob=1.0,
    )
    assert dose_with_iob == pytest.approx(dose_no_iob - 1.0)
    dose_with_dia = calc_bolus(
        carbs=50,
        current_bg=8,
        profile=profile,
        bolus_round_step=0.1,
        iob=1.0,
        dia=8.0,
    )
    assert dose_with_dia == pytest.approx(dose_no_iob - 0.5)


def test_calc_bolus_negative_max_bolus() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    with pytest.raises(ValueError, match="max_bolus must be non-negative"):
        calc_bolus(
            carbs=10,
            current_bg=7,
            profile=profile,
            max_bolus=-1.0,
        )
