import pytest
from stubs.bot_stub import extract_nutrition_info
from functions import calc_bolus, PatientProfile

@pytest.mark.parametrize("text, expected_carbs, expected_xe", [
    ("Углеводы: 37 г ± 3 г\nХЕ: 3,1 ± 0,2", 37, 3.1),
    ("ХЕ: 2,5 ± 0,1", None, 2.5),
    ("углеводы: 50 г", 50, None),
    ("20–25 г", 22.5, None),
    ("3–4 ХЕ", None, 3.5),
    ("нет данных", None, None),
])
def test_extract_nutrition_info(text, expected_carbs, expected_xe):
    carbs, xe = extract_nutrition_info(text)
    assert (carbs == expected_carbs or (carbs is None and expected_carbs is None))
    assert (xe == expected_xe or (xe is None and expected_xe is None))

def test_calc_bolus():
    profile = PatientProfile(icr=10, cf=2, target_bg=6)
    # meal: 50/10=5, correction: (10-6)/2=2, total=7
    assert calc_bolus(50, 10, profile) == 7.0
    # без коррекции
    assert calc_bolus(30, 6, profile) == 3.0
    # сахар ниже целевого — коррекция не добавляется
    assert calc_bolus(24, 4, profile) == 2.4


@pytest.mark.parametrize("icr, cf", [
    (0, 2),
    (-1, 2),
    (10, 0),
    (10, -1),
])
def test_calc_bolus_invalid_profile(icr, cf):
    profile = PatientProfile(icr=icr, cf=cf, target_bg=6)
    with pytest.raises(ValueError):
        calc_bolus(50, 10, profile)
