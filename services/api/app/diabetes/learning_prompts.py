"""Prompt templates for diabetes learning module."""

from __future__ import annotations

SYSTEM_TUTOR_RU = (
    "Ты — репетитор по диабету. "
    "Говори короткими предложениями. "
    "Сначала спрашивай, потом объясняй. "
    "Не давай советов по терапии. "
    "Всегда добавляй предупреждение: 'Проконсультируйтесь с врачом.'"
)

_DISCLAIMER_RU = "Проконсультируйтесь с врачом."


def _with_disclaimer(text: str) -> str:
    """Append a common disclaimer to *text*.

    Parameters
    ----------
    text: str
        Base text that requires the disclaimer.
    """
    base = text.strip()
    return f"{base} {_DISCLAIMER_RU}" if base else _DISCLAIMER_RU


def build_explain_step(step: str) -> str:
    """Build a prompt asking and explaining a learning step."""
    prompt = f"Что ты знаешь о {step}? Объясни.".strip()
    return _with_disclaimer(prompt)


def build_quiz_check(question: str, options: list[str]) -> str:
    """Build a prompt that checks knowledge with multiple options."""
    opts = "; ".join(options)
    prompt = f"{question}? Варианты: {opts}. Выбери один.".strip()
    return _with_disclaimer(prompt)


def build_feedback(correct: bool, explanation: str) -> str:
    """Build feedback for quiz answers."""
    prefix = "Верно." if correct else "Неверно."
    prompt = f"{prefix} {explanation}".strip()
    return _with_disclaimer(prompt)
