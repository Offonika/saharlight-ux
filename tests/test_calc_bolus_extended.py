from services.api.app.diabetes.utils.functions import (
    PatientProfile,
    calc_bolus_extended,
)


def test_rounding_steps() -> None:
    profile = PatientProfile(icr=9.0, cf=50.0, target_bg=5.5)
    dose_half = calc_bolus_extended(15, 6, profile, round_step=0.5)
    dose_full = calc_bolus_extended(15, 6, profile, round_step=1.0)
    assert dose_half == 1.5
    assert dose_full == 2.0


def test_unit_conversion() -> None:
    profile = PatientProfile(icr=9.0, cf=50.0, target_bg=5.5)
    dose_10 = calc_bolus_extended(
        1, 5.5, profile, unit="xe", grams_per_xe=10, round_step=0.5
    )
    dose_12 = calc_bolus_extended(
        1, 5.5, profile, unit="xe", grams_per_xe=12, round_step=0.5
    )
    assert dose_10 == 1.0
    assert dose_12 == 1.5


def test_max_bolus_cap() -> None:
    profile = PatientProfile(icr=1.0, cf=1.0, target_bg=5.0)
    dose = calc_bolus_extended(500, 20, profile, round_step=1.0, max_bolus=10.0)
    assert dose == 10.0
