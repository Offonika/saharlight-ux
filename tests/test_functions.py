# test_functions.py

import pytest

from services.api.app.diabetes.utils.functions import (
    _safe_float,
    extract_nutrition_info,
    smart_input,
    NutritionInfo,
)


def test_safe_float_with_spaces() -> None:
    assert _safe_float(" 1,5 ") == 1.5


def test_safe_float_none() -> None:
    assert _safe_float(None) is None


@pytest.mark.parametrize("value", ["NaN", "inf", "-inf"])
def test_safe_float_non_finite(value: str) -> None:
    assert _safe_float(value) is None


def test_extract_nutrition_info_simple() -> None:
    text = (
        "Вес: 100 г, Белки: 5 г, Жиры: 10 г, углеводы: 45 г, Калории: 200 ккал, "
        "ХЕ: 3.5"
    )
    info = extract_nutrition_info(text)
    assert info.portion_g == 100
    assert info.proteins_g == 5
    assert info.fats_g == 10
    assert info.carbs_g == 45
    assert info.calories_kcal == 200
    assert info.xe == 3.5


def test_extract_nutrition_info_ranges() -> None:
    text = (
        "Вес: 90-110 г, Белки: 5-7 г, Жиры: 8-12 г, Углеводы: 30–50 г, "
        "Калории: 180-220 ккал, XE: 2–3"
    )
    info = extract_nutrition_info(text)
    assert info.portion_g == 100  # (90+110)/2
    assert info.proteins_g == 6  # (5+7)/2
    assert info.fats_g == 10  # (8+12)/2
    assert info.carbs_g == 40  # (30+50)/2
    assert info.calories_kcal == 200  # (180+220)/2
    assert info.xe == 2.5  # (2+3)/2


def test_extract_nutrition_info_plus_minus() -> None:
    text = (
        "Вес: 100 ± 10 г, Белки: 6 ± 1 г, Жиры: 10 ± 2 г, "
        "углеводы: 45 г ± 5 г, Калории: 200 ± 20 ккал, XE: 3 ± 0.5"
    )
    info = extract_nutrition_info(text)
    assert info.portion_g == 100
    assert info.proteins_g == 6
    assert info.fats_g == 10
    assert info.carbs_g == 45
    assert info.calories_kcal == 200
    assert info.xe == 3


def test_extract_nutrition_info_plus_minus_no_colon() -> None:
    text = "В блюде 30 г ± 10 г углеводов и 2 ± 1 ХЕ"
    info = extract_nutrition_info(text)
    assert info.carbs_g == 30
    assert info.xe == 2


def test_extract_nutrition_info_plus_minus_with_comma() -> None:
    text = "углеводы: 10,5 г ± 0,5 г, ХЕ: 2,5 ± 0,5"
    info = extract_nutrition_info(text)
    assert info.carbs_g == pytest.approx(10.5)
    assert info.xe == pytest.approx(2.5)


def test_extract_nutrition_info_missing() -> None:
    text = "Нет данных"
    info = extract_nutrition_info(text)
    assert info == NutritionInfo()


def test_extract_nutrition_info_invalid_carbs() -> None:
    text = "углеводы: 5..2 г, ХЕ: 3"
    info = extract_nutrition_info(text)
    assert info.carbs_g is None
    assert info.xe == 3


def test_extract_nutrition_info_invalid_xe() -> None:
    text = "углеводы: 45 г, ХЕ: 1..2"
    info = extract_nutrition_info(text)
    assert info.carbs_g == 45
    assert info.xe is None


def test_extract_nutrition_info_ignores_title_line() -> None:
    text = "Борщ\nУглеводы: 25 г\nХЕ: 2"
    info = extract_nutrition_info(text)
    assert info.carbs_g == 25
    assert info.xe == 2


def test_extract_nutrition_info_first_line_with_data() -> None:
    text = "Углеводы: 25 г\nХЕ: 2"
    info = extract_nutrition_info(text)
    assert info.carbs_g == 25
    assert info.xe == 2


def test_extract_nutrition_info_first_line_xe_only() -> None:
    text = "ХЕ: 3\nПрочее"
    info = extract_nutrition_info(text)
    assert info.carbs_g is None
    assert info.xe == 3


def test_extract_nutrition_info_non_string() -> None:
    assert extract_nutrition_info(123) == NutritionInfo()


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
