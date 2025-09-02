from __future__ import annotations

import pytest

from services.api.app.diabetes.handlers.profile.validation import (
    MSG_CF_GT0,
    MSG_HIGH_GT_LOW,
    MSG_ICR_GT0,
    MSG_LOW_GT0,
    MSG_TARGET_GT0,
    MSG_TARGET_RANGE,
    parse_profile_args,
    validate_profile_numbers,
)


def test_parse_profile_args_positional() -> None:
    res = parse_profile_args(["1", "2", "3", "4", "5"])
    assert res == {
        "icr": "1",
        "cf": "2",
        "target": "3",
        "low": "4",
        "high": "5",
    }


def test_parse_profile_args_key_value() -> None:
    res = parse_profile_args(["ICR=1", "c=2", "tar=3", "L=4", "H=5"])
    assert res == {
        "icr": "1",
        "cf": "2",
        "target": "3",
        "low": "4",
        "high": "5",
    }


@pytest.mark.parametrize(
    "args",
    [
        ["icr=1", "cf=2"],
        ["foo=1", "cf=2", "target=3", "low=4", "high=5"],
        ["icr=1", "cf=2", "target=3", "low=4", "bad"],
    ],
)
def test_parse_profile_args_invalid(args: list[str]) -> None:
    assert parse_profile_args(args) is None


@pytest.mark.parametrize(
    "nums, msg",
    [
        ((0, 1, 2, 3, 4), MSG_ICR_GT0),
        ((1, 0, 2, 3, 4), MSG_CF_GT0),
        ((1, 2, 0, 3, 4), MSG_TARGET_GT0),
        ((1, 2, 3, 0, 4), MSG_LOW_GT0),
        ((1, 2, 3, 4, 3), MSG_HIGH_GT_LOW),
        ((1, 2, 5, 1, 4), MSG_TARGET_RANGE),
    ],
)
def test_validate_profile_numbers_errors(
    nums: tuple[float, float, float, float, float], msg: str
) -> None:
    assert validate_profile_numbers(*nums) == msg


def test_validate_profile_numbers_success() -> None:
    assert validate_profile_numbers(1, 2, 5, 3, 7) is None
