"""Tests for learning prompt builders."""

from __future__ import annotations

import pytest

from services.api.app.diabetes.prompts import (
    SYSTEM_TUTOR_RU,
    build_explain_step,
    build_feedback,
    build_quiz_check,
    build_system_prompt,
    build_user_prompt_step,
    disclaimer,
)
from services.api.app.diabetes.llm_router import LLMTask


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
def test_builder_functions_without_disclaimer(builder: object, kwargs: dict[str, object]) -> None:
    """Builders should return non-empty text without the disclaimer."""

    text = builder(**kwargs)  # type: ignore[arg-type]
    assert text
    assert disclaimer() not in text


@pytest.mark.parametrize(
    ("correct", "prefix"),
    [(True, "Верно."), (False, "Неверно.")],
)
def test_build_feedback_variants(correct: bool, prefix: str) -> None:
    """Feedback builder should handle both correct and incorrect paths."""

    text = build_feedback(correct, "Пояснение")
    assert text
    assert text.startswith(prefix)
    assert disclaimer() not in text


def test_build_system_prompt_limits_length() -> None:
    """System prompt should contain warnings and stay within 1.5k chars."""

    prompt = build_system_prompt({"age_group": "adult"})
    assert "Не назначай" in prompt
    assert "вопросом-проверкой" in prompt
    assert len(prompt) <= 1_500


def test_build_user_prompt_step_trims_and_ends_with_instruction() -> None:
    """User prompt builder must trim long text and keep final instruction."""

    long_summary = "x" * 2_000
    prompt = build_user_prompt_step("xe_basics", 1, long_summary)
    assert len(prompt) <= 1_500
    assert prompt.endswith("Ответ не показывай.")


def test_build_system_prompt_warns_on_unknown_type() -> None:
    """Include warning when diabetes type is unknown."""

    prompt = build_system_prompt({"diabetes_type": "unknown"})
    assert "Тип диабета не определён — избегай тип-специфичных рекомендаций." in prompt

def test_system_prompt_avoids_type_specific_mentions_when_unknown() -> None:
    """When diabetes type is unknown no T1/T2 hints appear."""

    prompt = build_system_prompt({})
    assert "Тип диабета не определён" in prompt
    assert "T1" not in prompt
    assert "T2" not in prompt


def test_build_system_prompt_quiz_check_instructions() -> None:
    """QUIZ_CHECK task adds answer format instructions."""

    prompt = build_system_prompt({}, task=LLMTask.QUIZ_CHECK)
    assert "✅" in prompt and "⚠️" in prompt and "❌" in prompt
    assert "Не задавай вопросов" in prompt
