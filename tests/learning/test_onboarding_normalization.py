from __future__ import annotations

import pytest

from services.api.app.diabetes.learning_onboarding import (
    _norm_age_group,
    _norm_level,
)


def test_norm_age_group_numeric() -> None:
    assert _norm_age_group("49") == "adult"


@pytest.mark.parametrize(
    ("text", "code"),
    [("подросток", "teen"), ("взрослый", "adult"), ("60+", "60+")],
)
def test_norm_age_group_russian(text: str, code: str) -> None:
    assert _norm_age_group(text) == code
def test_norm_level_numeric() -> None:
    assert _norm_level("0") == "novice"


def test_norm_level_russian_advanced() -> None:
    assert _norm_level("продвинутый") == "expert"
