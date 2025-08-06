from datetime import time, timedelta

import pytest

from diabetes.utils import parse_time_interval, INVALID_TIME_MSG


def test_parse_time_success():
    assert parse_time_interval("22:30") == time(22, 30)
    assert parse_time_interval("6:00") == time(6, 0)


def test_parse_interval_success():
    assert parse_time_interval("5h") == timedelta(hours=5)
    assert parse_time_interval("3d") == timedelta(days=3)


@pytest.mark.parametrize("value", ["", "25:00", "5x", "1:60"])
def test_parse_time_invalid(value):
    with pytest.raises(ValueError) as exc:
        parse_time_interval(value)
    assert str(exc.value) == INVALID_TIME_MSG
