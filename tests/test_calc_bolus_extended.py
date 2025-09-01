import pytest

from services.api.app.diabetes.utils import calc_bolus as cb
from services.api.app.diabetes.utils.calc_bolus import PatientProfile


def test_rounding_step_one() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    dose = cb.calc_bolus(
        carbs=43,
        current_bg=8,
        profile=profile,
        bolus_round_step=1.0,
    )
    assert dose == 5.0


def test_unit_conversion_custom_xe(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = PatientProfile(icr=12, cf=2, target_bg=6)
    monkeypatch.setattr(cb, "XE_GRAMS", 10)
    dose_xe = cb.calc_bolus(
        carbs=5,
        current_bg=6,
        profile=profile,
        carb_units="xe",
        bolus_round_step=0.1,
    )
    dose_g = cb.calc_bolus(
        carbs=50,
        current_bg=6,
        profile=profile,
        carb_units="g",
        bolus_round_step=0.1,
    )
    assert dose_xe == dose_g


def test_max_bolus_capped_and_rounded() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    dose = cb.calc_bolus(
        carbs=100,
        current_bg=6,
        profile=profile,
        bolus_round_step=0.5,
        max_bolus=6.3,
    )
    assert dose == 6.0
