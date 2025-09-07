from __future__ import annotations

from services.api.app.diabetes.learning_onboarding import (
    _norm_age_group,
    _norm_diabetes_type,
    _norm_level,
)


def test_norm_age_group_numeric() -> None:
    assert _norm_age_group("49") == "adult"


def test_norm_diabetes_type_numeric() -> None:
    assert _norm_diabetes_type("2") == "T2"


def test_norm_level_numeric() -> None:
    assert _norm_level("0") == "novice"


def test_norm_level_russian() -> None:
    assert _norm_level("Новичок") == "novice"
    assert _norm_level("эксперт") == "expert"
