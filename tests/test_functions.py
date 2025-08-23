# test_functions.py

from decimal import getcontext

import pytest

from services.api.app.diabetes.utils.functions import (
    PatientProfile,
    _safe_float,
    calc_bolus,
    extract_nutrition_info,
    smart_input,
)


def test_safe_float_with_spaces() -> None:
    assert _safe_float(" 1,5 ") == 1.5


def test_safe_float_none() -> None:
    assert _safe_float(None) is None


@pytest.mark.parametrize("value", ["NaN", "inf", "-inf"])
def test_safe_float_non_finite(value: str) -> None:
    assert _safe_float(value) is None


def test_calc_bolus_basic() -> None:
    profile = PatientProfile(icr=12, cf=2, target_bg=6)
    result = calc_bolus(carbs_g=60, current_bg=8, profile=profile)
    # meal=60/12=5, correction=(8-6)/2=1, total=6.0
    assert result == 6.0


def test_calc_bolus_no_correction() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    result = calc_bolus(carbs_g=30, current_bg=5, profile=profile)
    # meal=3, correction=max(0, (5-6)/2)=0, total=3.0
    assert result == 3.0


def test_calc_bolus_decimal_precision() -> None:
    profile = PatientProfile(icr=3, cf=1, target_bg=5)
    result = calc_bolus(carbs_g=1, current_bg=5, profile=profile)
    assert result == 0.3


def test_calc_bolus_no_precision_leak() -> None:
    ctx = getcontext()
    original = ctx.prec
    ctx.prec = 10
    profile = PatientProfile(icr=12, cf=2, target_bg=6)
    calc_bolus(carbs_g=60, current_bg=8, profile=profile)
    assert ctx.prec == 10
    ctx.prec = original


def test_calc_bolus_invalid_icr() -> None:
    profile = PatientProfile(icr=0, cf=2, target_bg=6)
    with pytest.raises(ValueError, match="icr"):
        calc_bolus(carbs_g=30, current_bg=5, profile=profile)


def test_calc_bolus_invalid_cf() -> None:
    profile = PatientProfile(icr=10, cf=-1, target_bg=6)
    with pytest.raises(ValueError, match="cf"):
        calc_bolus(carbs_g=30, current_bg=5, profile=profile)


def test_calc_bolus_invalid_target_bg() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=-1)
    with pytest.raises(ValueError, match="target_bg"):
        calc_bolus(carbs_g=30, current_bg=5, profile=profile)


def test_calc_bolus_negative_carbs() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    with pytest.raises(ValueError, match="carbs_g"):
        calc_bolus(carbs_g=-5, current_bg=5, profile=profile)


def test_calc_bolus_negative_current_bg() -> None:
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    with pytest.raises(ValueError, match="current_bg"):
        calc_bolus(carbs_g=30, current_bg=-1, profile=profile)


def test_extract_nutrition_info_simple() -> None:
    text = "углеводы: 45 г, ХЕ: 3.5"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 45
    assert xe == 3.5


def test_extract_nutrition_info_ranges() -> None:
    text = "Углеводы: 30–50 г, XE: 2–3"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 40  # (30+50)/2
    assert xe == 2.5  # (2+3)/2


def test_extract_nutrition_info_plus_minus() -> None:
    text = "углеводы: 45 г ± 5 г, XE: 3 ± 0.5"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 45
    assert xe == 3


def test_extract_nutrition_info_plus_minus_no_colon() -> None:
    text = "В блюде 30 г ± 10 г углеводов и 2 ± 1 ХЕ"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 30
    assert xe == 2


def test_extract_nutrition_info_plus_minus_with_comma() -> None:
    text = "углеводы: 10,5 г ± 0,5 г, ХЕ: 2,5 ± 0,5"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == pytest.approx(10.5)
    assert xe == pytest.approx(2.5)


def test_extract_nutrition_info_missing() -> None:
    text = "Нет данных"
    carbs, xe = extract_nutrition_info(text)
    assert carbs is None
    assert xe is None


def test_extract_nutrition_info_invalid_carbs() -> None:
    text = "углеводы: 5..2 г, ХЕ: 3"
    carbs, xe = extract_nutrition_info(text)
    assert carbs is None
    assert xe == 3


def test_extract_nutrition_info_invalid_xe() -> None:
    text = "углеводы: 45 г, ХЕ: 1..2"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 45
    assert xe is None


def test_extract_nutrition_info_ignores_title_line() -> None:
    text = "Борщ\nУглеводы: 25 г\nХЕ: 2"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 25
    assert xe == 2


def test_extract_nutrition_info_first_line_with_data() -> None:
    text = "Углеводы: 25 г\nХЕ: 2"
    carbs, xe = extract_nutrition_info(text)
    assert carbs == 25
    assert xe == 2


def test_extract_nutrition_info_first_line_xe_only() -> None:
    text = "ХЕ: 3\nПрочее"
    carbs, xe = extract_nutrition_info(text)
    assert carbs is None
    assert xe == 3


def test_extract_nutrition_info_non_string() -> None:
    assert extract_nutrition_info(123) == (None, None)


def test_smart_input_basic() -> None:
    msg = "sugar=7 xe=3 dose=4"
    assert smart_input(msg) == {"sugar": 7.0, "xe": 3.0, "dose": 4.0}


def test_smart_input_units_without_labels() -> None:
    msg = "7 ммоль/л, 3 XE, 4 ед"
    assert smart_input(msg) == {"sugar": 7.0, "xe": 3.0, "dose": 4.0}


def test_smart_input_localized_terms() -> None:
    msg = "сахар:5,5 доза=2,5"
    assert smart_input(msg) == {
        "sugar": pytest.approx(5.5),
        "xe": None,
        "dose": pytest.approx(2.5),
    }


def test_smart_input_unit_mixup() -> None:
    with pytest.raises(ValueError):
        smart_input("сахар 7 XE")


def test_smart_input_unit_mixup_xe() -> None:
    with pytest.raises(ValueError):
        smart_input("xe 5 ммоль/л")


def test_smart_input_unit_mixup_dose() -> None:
    with pytest.raises(ValueError):
        smart_input("доза 7 ммоль")
