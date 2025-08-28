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
    "field,value,message",
    [
        ("icr", 0.0, "icr must be greater than 0"),
        ("cf", 0.0, "cf must be greater than 0"),
        ("target", 0.0, "target must be greater than 0"),
        ("low", 0.0, "low must be greater than 0"),
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
    }
    kwargs[field] = value
    data = ProfileSchema(**kwargs)
    with pytest.raises(ValueError) as exc:
        _validate_profile(data)
    assert str(exc.value) == message


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


def test_profile_schema_computes_target_when_missing() -> None:
    data = ProfileSchema(
        telegramId=1,
        icr=1.0,
        cf=1.0,
        low=4.0,
        high=6.0,
    )
    assert data.target == 5.0


def test_profile_schema_low_alias_mismatch() -> None:
    with pytest.raises(ValidationError):
        ProfileSchema(
            telegramId=1,
            icr=1.0,
            cf=1.0,
            low=4.0,
            targetLow=5.0,
            high=6.0,
        )


def test_profile_schema_high_alias_mismatch() -> None:
    with pytest.raises(ValidationError):
        ProfileSchema(
            telegramId=1,
            icr=1.0,
            cf=1.0,
            low=4.0,
            high=6.0,
            targetHigh=7.0,
        )


def test_profile_schema_requires_low_less_than_high() -> None:
    with pytest.raises(ValidationError):
        ProfileSchema(
            telegramId=1,
            icr=1.0,
            cf=1.0,
            target=5.0,
            low=5.0,
            high=4.0,
        )


def test_profile_schema_high_positive() -> None:
    with pytest.raises(ValidationError):
        ProfileSchema(
            telegramId=1,
            icr=1.0,
            cf=1.0,
            target=5.0,
            low=4.0,
            high=0.0,
        )
