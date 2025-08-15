from typing import Any

import pytest
from fastapi import HTTPException

from services.api.app.schemas.profile import ProfileSchema
from services.api.app.services.profile import _validate_profile


def test_validate_profile_allows_target_between_limits() -> None:
    data = ProfileSchema(
        telegram_id=1,
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
        telegram_id=1,
        icr=1.0,
        cf=1.0,
        target=target,
        low=4.0,
        high=7.0,
    )
    with pytest.raises(HTTPException) as exc:
        _validate_profile(data)
    assert exc.value.status_code == 400
    assert exc.value.detail == "target must be between low and high"