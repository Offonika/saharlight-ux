from typing import Any

import pytest

from services.api.app.diabetes.utils.functions import smart_input


@pytest.mark.parametrize(
    "message, expected",
    [
        ("sugar=7 xe=2.5 dose=4", {"sugar": 7.0, "xe": 2.5, "dose": 4.0}),
        ("7 ммоль/л, 3 XE", {"sugar": 7.0, "xe": 3.0, "dose": None}),
        ("сахар 5 XE 3.2 доза 6", {"sugar": 5.0, "xe": 3.2, "dose": 6.0}),
        ("Xe 1.5 dose 2", {"sugar": None, "xe": 1.5, "dose": 2.0}),
        ("5 ммоль/л", {"sugar": 5.0, "xe": None, "dose": None}),
        ("5 XE", {"sugar": None, "xe": 5.0, "dose": None}),
        ("4 units", {"sugar": None, "xe": None, "dose": 4.0}),
        ("sugar=2.5", {"sugar": 2.5, "xe": None, "dose": None}),
    ],
)
def test_smart_input_valid_cases(message: Any, expected: Any) -> None:
    assert smart_input(message) == expected


def test_smart_input_invalid_dose() -> None:
    with pytest.raises(ValueError):
        smart_input("доза=abc")


@pytest.mark.parametrize("message", ["sugar=7abc", "xe=3foo", "dose=4bar"])
def test_smart_input_rejects_garbage(message: str) -> None:
    with pytest.raises(ValueError):
        smart_input(message)


@pytest.mark.parametrize("message", ["5", " 7 ", "2."])
def test_smart_input_plain_number(message: str) -> None:
    with pytest.raises(ValueError):
        smart_input(message)


def test_smart_input_invalid_decimal() -> None:
    with pytest.raises(ValueError):
        smart_input("sugar=2.")
