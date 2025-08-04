# test_functions.py

import pytest

from diabetes.functions import (
    PatientProfile,
    _safe_float,
    calc_bolus,
    extract_nutrition_info,
)


def test_safe_float_with_spaces():
    assert _safe_float(" 1,5 ") == 1.5


def test_safe_float_none():
    assert _safe_float(None) is None


def test_calc_bolus_basic():
    profile = PatientProfile(icr=12, cf=2, target_bg=6)
    result = calc_bolus(carbs_g=60, current_bg=8, profile=profile)
    # meal=60/12=5, correction=(8-6)/2=1, total=6.0
    assert result == 6.0


def test_calc_bolus_no_correction():
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    result = calc_bolus(carbs_g=30, current_bg=5, profile=profile)
    # meal=3, correction=max(0, (5-6)/2)=0, total=3.0
    assert result == 3.0


def test_calc_bolus_invalid_icr():
    profile = PatientProfile(icr=0, cf=2, target_bg=6)
    with pytest.raises(ValueError, match="icr"):
        calc_bolus(carbs_g=30, current_bg=5, profile=profile)


def test_calc_bolus_invalid_cf():
    profile = PatientProfile(icr=10, cf=-1, target_bg=6)
    with pytest.raises(ValueError, match="cf"):
        calc_bolus(carbs_g=30, current_bg=5, profile=profile)


def test_calc_bolus_invalid_target_bg():
    profile = PatientProfile(icr=10, cf=2, target_bg=-1)
    with pytest.raises(ValueError, match="target_bg"):
        calc_bolus(carbs_g=30, current_bg=5, profile=profile)


def test_calc_bolus_negative_carbs():
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    with pytest.raises(ValueError, match="carbs_g"):
        calc_bolus(carbs_g=-5, current_bg=5, profile=profile)


def test_calc_bolus_negative_current_bg():
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    with pytest.raises(ValueError, match="current_bg"):
        calc_bolus(carbs_g=30, current_bg=-1, profile=profile)


def test_extract_nutrition_info_simple():
    text = "углеводы: 45 г, ХЕ: 3.5"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 45
    assert xe == 3.5


def test_extract_nutrition_info_ranges():
    text = "Углеводы: 30–50 г, XE: 2–3"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 40  # (30+50)/2
    assert xe == 2.5    # (2+3)/2


def test_extract_nutrition_info_plus_minus():
    text = "углеводы: 45 г ± 5 г, XE: 3 ± 0.5"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 45
    assert xe == 3


def test_extract_nutrition_info_plus_minus_no_colon():
    text = "В блюде 30 г ± 10 г углеводов и 2 ± 1 ХЕ"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 30
    assert xe == 2


def test_extract_nutrition_info_plus_minus_with_comma():
    text = "углеводы: 10,5 г ± 0,5 г, ХЕ: 2,5 ± 0,5"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == pytest.approx(10.5)
    assert xe == pytest.approx(2.5)


def test_extract_nutrition_info_missing():
    text = "Нет данных"
    carbs, xe = extract_nutrition_info(text)
    assert carbs is None
    assert xe is None


def test_extract_nutrition_info_invalid_carbs():
    text = "углеводы: 5..2 г, ХЕ: 3"
    carbs, xe = extract_nutrition_info(text)
    assert carbs is None
    assert xe == 3


def test_extract_nutrition_info_invalid_xe():
    text = "углеводы: 45 г, ХЕ: 1..2"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 45
    assert xe is None


def test_extract_nutrition_info_ignores_title_line():
    text = "Борщ\nУглеводы: 25 г\nХЕ: 2"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 25
    assert xe == 2


def test_extract_nutrition_info_non_string():
    assert extract_nutrition_info(123) == (None, None)
