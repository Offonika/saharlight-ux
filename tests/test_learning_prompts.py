from services.api.app.diabetes.learning_prompts import (
    SYSTEM_TUTOR_RU,
    build_explain_step,
    build_feedback,
    build_quiz_check,
    disclaimer,
)


def test_disclaimer_returns_warning() -> None:
    assert disclaimer() == "Проконсультируйтесь с врачом."


def test_system_tutor_contains_disclaimer() -> None:
    assert disclaimer() in SYSTEM_TUTOR_RU


def test_build_explain_step_appends_disclaimer() -> None:
    text = build_explain_step("инсулин")
    assert text.endswith(disclaimer())
    assert text


def test_build_quiz_check_lists_options() -> None:
    options = ["утром", "вечером"]
    text = build_quiz_check("Когда измерять сахар", options)
    assert all(opt in text for opt in options)
    assert text.endswith(disclaimer())
    assert text


def test_build_feedback_prefix_and_disclaimer() -> None:
    text = build_feedback(True, "Все верно")
    assert text.startswith("Верно.")
    assert text.endswith(disclaimer())
    assert text
