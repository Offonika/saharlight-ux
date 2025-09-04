from __future__ import annotations

from typing import Any, Callable

import pytest

from services.api.app.diabetes.learning_prompts import (
    SYSTEM_TUTOR_RU,
    _DISCLAIMER_RU,
    build_explain_step,
    build_feedback,
    build_quiz_check,
)


def test_system_tutor_contains_disclaimer() -> None:
    assert _DISCLAIMER_RU in SYSTEM_TUTOR_RU


@pytest.mark.parametrize(
    ("builder", "args"),
    [
        (build_explain_step, ("инсулин",)),
        (build_quiz_check, ("Когда измерять сахар", ["утром", "вечером"])),
    ],
)
def test_builders_return_text_with_disclaimer(
    builder: Callable[..., str], args: tuple[Any, ...]
) -> None:
    text = builder(*args)
    assert text
    assert text.endswith(_DISCLAIMER_RU)


@pytest.mark.parametrize(
    ("correct", "prefix"),
    [
        (True, "Верно."),
        (False, "Неверно."),
    ],
)
def test_build_feedback_paths(correct: bool, prefix: str) -> None:
    text = build_feedback(correct, "Пояснение")
    assert text
    assert text.startswith(prefix)
    assert text.endswith(_DISCLAIMER_RU)
