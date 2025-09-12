from __future__ import annotations

from services.api.app.diabetes.prompts import (
    build_system_prompt,
    build_user_prompt_step,
)
from services.api.app.diabetes.llm_router import LLMTask


def test_build_system_prompt_includes_profile() -> None:
    profile = {
        "diabetes_type": "1",
        "therapyType": "pump",
        "learning_level": "novice",
        "carbUnits": "XE",
        "age_group": "teen",
    }
    prompt = build_system_prompt(profile)
    assert "тип диабета=1" in prompt
    assert "терапия=pump" in prompt
    assert "углеводы=XE" in prompt
    assert "простым языком, дружелюбно" in prompt


def test_build_user_prompt_step_contains_goal_and_instruction() -> None:
    long_summary = "prev" * 200
    prompt = build_user_prompt_step("xe_basics", 2, long_summary)
    assert "xe_basics" in prompt
    assert "Номер шага: 2" in prompt
    assert prompt.endswith("Ответ не показывай.")
    assert len(prompt) <= 1_500


def test_build_system_prompt_quiz_check_format() -> None:
    prompt = build_system_prompt({}, task=LLMTask.QUIZ_CHECK)
    assert "✅" in prompt and "⚠️" in prompt and "❌" in prompt
    assert "Не задавай вопросов" in prompt
