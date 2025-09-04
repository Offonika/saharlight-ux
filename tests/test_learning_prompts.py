"""Tests for learning prompt builders."""

from __future__ import annotations

import pytest

from services.api.app.diabetes.learning_prompts import (
    SYSTEM_TUTOR_RU,
    build_explain_step,
    build_feedback,
    build_quiz_check,
    disclaimer,
)


def test_disclaimer_returns_warning() -> None:
    """Ensure the disclaimer text matches the expected warning."""

    assert disclaimer() == "Проконсультируйтесь с врачом."


def test_system_tutor_contains_disclaimer() -> None:
    """`SYSTEM_TUTOR_RU` must embed the disclaimer."""

    assert disclaimer() in SYSTEM_TUTOR_RU


@pytest.mark.parametrize(
    ("builder", "kwargs"),
    [
        (build_explain_step, {"step": "инсулин"}),
        (
            build_quiz_check,
            {
                "question": "Когда измерять сахар",
                "options": ["утром", "вечером"],
            },
        ),
    ],
)
def test_builder_functions_append_disclaimer(
    builder: object, kwargs: dict[str, object]
) -> None:
    """All builders should return non-empty text with the disclaimer."""

    text = builder(**kwargs)  # type: ignore[arg-type]
    assert text
    assert text.endswith(disclaimer())


@pytest.mark.parametrize(
    ("correct", "prefix"),
    [(True, "Верно."), (False, "Неверно.")],
)
def test_build_feedback_variants(correct: bool, prefix: str) -> None:
    """Feedback builder should handle both correct and incorrect paths."""

    text = build_feedback(correct, "Пояснение")
    assert text
    assert text.startswith(prefix)
    assert text.endswith(disclaimer())

