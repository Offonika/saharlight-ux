from __future__ import annotations

from services.api.app.diabetes import learning_prompts


def test_disclaimer_text() -> None:
    text = learning_prompts.disclaimer()
    assert "educational" in text.lower()
    assert "medical" in text.lower()


def test_explain_step_uses_disclaimer() -> None:
    messages = learning_prompts.explain_step_prompt("What is diabetes?")
    assert messages[0]["content"] == learning_prompts.disclaimer()


def test_quiz_check_uses_disclaimer() -> None:
    messages = learning_prompts.quiz_check_prompt("Q?", ["A", "B"], 1)
    assert messages[0]["content"] == learning_prompts.disclaimer()


def test_long_plan_uses_disclaimer() -> None:
    messages = learning_prompts.long_plan_prompt("Stay healthy")
    assert messages[0]["content"] == learning_prompts.disclaimer()
