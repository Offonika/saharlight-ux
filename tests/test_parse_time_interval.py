from datetime import time, timedelta

import pytest

from diabetes.utils import INVALID_TIME_MSG, parse_time_interval


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("09:30", time(9, 30)),
        ("9:30", time(9, 30)),
        ("22:30", time(22, 30)),
        ("6:00", time(6, 0)),
    ],
)
def test_parse_time_success(text, expected):
    assert parse_time_interval(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5h", timedelta(hours=5)),
        ("3d", timedelta(days=3)),
    ],
)
def test_parse_interval_success(text, expected):
    assert parse_time_interval(text) == expected


@pytest.mark.parametrize(
    "value",
    ["", "25:00", "5x", "1:60", "2h30", "3 d"],
)
def test_parse_time_invalid(value):
    with pytest.raises(ValueError) as exc:
        parse_time_interval(value)
    assert str(exc.value) == INVALID_TIME_MSG
