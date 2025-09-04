from __future__ import annotations

import pytest

from services.api.app.diabetes.learning_prompts import (
    _DISCLAIMER_RU,
    build_explain_step,
    build_feedback,
    build_quiz_check,
)


@pytest.mark.parametrize(
    "builder,args",
    [
        (build_explain_step, ("углеводы",)),
        (build_quiz_check, ("Что такое ХЕ", ["12", "24"])),
    ],
)
def test_builders_include_disclaimer(builder, args) -> None:
    result = builder(*args)
    assert result
    assert _DISCLAIMER_RU in result


@pytest.mark.parametrize("correct,prefix", [(True, "Верно."), (False, "Неверно.")])
def test_build_feedback_paths(correct: bool, prefix: str) -> None:
    result = build_feedback(correct, "объяснение")
    assert result
    assert prefix in result
    assert _DISCLAIMER_RU in result
