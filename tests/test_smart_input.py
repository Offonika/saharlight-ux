import pytest

from diabetes.functions import smart_input


@pytest.mark.parametrize(
    "message, expected",
    [
        ("sugar=7 xe=2.5 dose=4", {"sugar": 7.0, "xe": 2.5, "dose": 4.0}),
        ("7 ммоль/л, 3 XE", {"sugar": 7.0, "xe": 3.0, "dose": None}),
        ("сахар 5 XE 3.2 доза 6", {"sugar": 5.0, "xe": 3.2, "dose": 6.0}),
        ("Xe 1.5 dose 2", {"sugar": None, "xe": 1.5, "dose": 2.0}),
    ],
)
def test_smart_input_valid_cases(message, expected):
    assert smart_input(message) == expected


def test_smart_input_invalid_dose():
    with pytest.raises(ValueError):
        smart_input("доза=abc")
