# test_functions.py

import pytest

from services.api.app.diabetes.utils.functions import (
    _safe_float,
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
