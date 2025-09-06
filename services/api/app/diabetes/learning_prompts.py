"""Prompt templates for diabetes learning module."""

from __future__ import annotations

from collections.abc import Mapping
from textwrap import dedent


MAX_PROMPT_LEN = 1_500


def _trim(text: str, limit: int = MAX_PROMPT_LEN) -> str:
    """Ensure *text* does not exceed ``limit`` characters."""

    return text[:limit]


def disclaimer() -> str:
    """Return the standard medical warning."""
    return "Проконсультируйтесь с врачом."


SYSTEM_TUTOR_RU = (
    "Ты — репетитор по диабету. "
    "Говори короткими предложениями. "
    "Сначала спрашивай, потом объясняй. "
    "Не давай советов по терапии. "
    f"Всегда добавляй предупреждение: '{disclaimer()}'"
)


def _with_disclaimer(text: str) -> str:
    """Append a common disclaimer to *text*.

    Parameters
    ----------
    text: str
        Base text that requires the disclaimer.
    """
    base = text.strip()
    tail = disclaimer()
    return f"{base} {tail}" if base else tail


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


def build_system_prompt(p: Mapping[str, str | None]) -> str:
    """Build a system prompt tailored to the user *p* profile."""

    tone = {
        "teen": "простым языком, дружелюбно",
        "adult": "ясно и по делу",
        "60+": "очень простыми фразами, поддерживающе",
    }.get(p.get("age_group") or "", "ясно и просто")
    prompt = dedent(
        f"""
        Ты — персональный тьютор по диабету. Подстраивайся под пользователя.
        Профиль: тип диабета={p.get('diabetes_type', 'unknown')},
        терапия={p.get('therapyType', 'unknown')},
        уровень={p.get('learning_level', 'novice')},
        углеводы={p.get('carbUnits', 'XE')}. Тон: {tone}.
        Пиши коротко (2–4 предложения). Каждый шаг заканчивай ОДНИМ
        вопросом-проверкой.
        Не назначай лечение/дозировки; при сомнениях — советуй обсудить
        с врачом.
        """
    ).strip()
    return _trim(prompt)


def build_user_prompt_step(
    topic_slug: str, step_idx: int, prev_summary: str | None
) -> str:
    """Build a user-level prompt for a learning step."""

    goals = {
        "xe_basics": "объяснить, что такое ХЕ (~10–12 г углеводов) на простых примерах",
        "healthy-eating": "дать 3 базовых правила питания и один применимый совет",
        "basics-of-diabetes": "кратко: что такое сахар крови, зачем замеры",
        "insulin-usage": "связь углеводов и короткого инсулина на уровне принципов (без доз)",
    }
    goal = goals.get(topic_slug, "дать понятный шаг по теме")
    summary = (prev_summary or "—")[:400]
    prompt = (
        f"Тема: {topic_slug}. Цель шага: {goal}. Номер шага: {step_idx}. "
        f"Резюме предыдущего: {summary}. "
        "Сначала объясни, затем задай один вопрос. Ответ не показывай."
    )
    return _trim(prompt)
