from typing import Any

import pytest
from pydantic import ValidationError

from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services.profile import _validate_profile


def test_validate_profile_allows_target_between_limits() -> None:
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=5.0,
        low=4.0,
        high=7.0,
    )
    _validate_profile(data)


@pytest.mark.parametrize("target", [3.0, 8.0])
def test_validate_profile_rejects_target_outside_limits(target: Any) -> None:
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=target,
        low=4.0,
        high=7.0,
    )
    with pytest.raises(ValueError) as exc:
        _validate_profile(data)
    assert str(exc.value) == "target must be between low and high"



@pytest.mark.parametrize(
    "field,value",
    [("quietStart", "25:00"), ("quietEnd", "bad")],
)
def test_profile_rejects_malformed_quiet_times(field: str, value: str) -> None:
    kwargs = {
        "telegramId": 1,
        "icr": 1.0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 7.0,
    }
    kwargs[field] = value
    with pytest.raises(ValidationError):
        ProfileSchema(**kwargs)

