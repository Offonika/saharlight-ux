from typing import Any

import pytest
from pydantic import ValidationError

from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services.profile import _validate_profile


def test_validate_profile_allows_computed_target() -> None:
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        low=4.0,
        high=6.0,
        therapyType="insulin",
    )
    _validate_profile(data)
    assert data.target == 5.0


@pytest.mark.parametrize("target", [3.0, 8.0])
def test_validate_profile_rejects_target_outside_limits(target: Any) -> None:
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        target=target,
        low=4.0,
        high=7.0,
        therapyType="insulin",
    )
    with pytest.raises(ValueError) as exc:
        _validate_profile(data)
    assert str(exc.value) == "target must be between low and high"


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("icr", 0.0, "icr must be greater than 0"),
        ("cf", 0.0, "cf must be greater than 0"),
        ("target", 0.0, "target must be greater than 0"),
        ("low", 0.0, "low must be greater than 0"),
        ("high", 0.0, "high must be greater than 0"),
        ("low_high", (5.0, 4.0), "low must be less than high"),
    ],
)
def test_validate_profile_rejects_invalid_values(
    field: str, value: Any, message: str
) -> None:
    kwargs = {
        "telegramId": 1,
        "icr": 1.0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 7.0,
        "therapyType": "insulin",
    }
    if field == "low_high":
        kwargs["low"], kwargs["high"] = value
    else:
        kwargs[field] = value
    data = ProfileSchema(**kwargs)
    with pytest.raises(ValueError) as exc:
        _validate_profile(data)
    assert str(exc.value) == message


@pytest.mark.parametrize("field", ["icr", "cf", "low", "high"])
def test_validate_profile_allows_missing_fields(field: str) -> None:
    kwargs = {
        "telegramId": 1,
        "icr": 1.0,
        "cf": 1.0,
        "low": 4.0,
        "high": 7.0,
        "therapyType": "insulin",
    }
    kwargs.pop(field)
    data = ProfileSchema(**kwargs)
    _validate_profile(data)


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
        "therapyType": "insulin",
    }
    kwargs[field] = value
    with pytest.raises(ValidationError):
        ProfileSchema(**kwargs)


@pytest.mark.parametrize("therapy_type", ["tablets", "none"])
def test_validate_profile_skips_icr_cf_for_non_insulin(therapy_type: str) -> None:
    data = ProfileSchema(
        telegramId=1,
        target=5.0,
        low=4.0,
        high=6.0,
        therapyType=therapy_type,
    )
    _validate_profile(data)
