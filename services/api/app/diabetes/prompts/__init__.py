"""Central storage for GPT prompt templates and instructions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
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


def build_explain_step(step: str) -> str:
    """Build a prompt asking and explaining a learning step."""

    prompt = f"Что ты знаешь о {step}? Объясни.".strip()
    return prompt


def build_quiz_check(question: str, options: list[str]) -> str:
    """Build a prompt that checks knowledge with multiple options."""

    opts = "; ".join(options)
    prompt = f"{question}? Варианты: {opts}. Выбери один.".strip()
    return prompt


def build_feedback(correct: bool, explanation: str) -> str:
    """Build feedback for quiz answers."""

    prefix = "Верно." if correct else "Неверно."
    prompt = f"{prefix} {explanation}".strip()
    return prompt


def build_system_prompt(p: Mapping[str, str | None]) -> str:
    """Build a system prompt tailored to the user *p* profile."""

    tone = {
        "teen": "простым языком, дружелюбно",
        "adult": "ясно и по делу",
        "60+": "очень простыми фразами, поддерживающе",
    }.get(p.get("age_group") or "", "ясно и просто")
    diabetes_type = p.get("diabetes_type") or "unknown"
    prompt = dedent(
        f"""
        Ты — персональный тьютор по диабету. Подстраивайся под пользователя.
        Профиль: тип диабета={diabetes_type},
        терапия={p.get("therapyType", "unknown")},
        уровень={p.get("learning_level", "novice")},
        углеводы={p.get("carbUnits", "XE")}. Тон: {tone}.
        Пиши коротко (2–4 предложения). Каждый шаг заканчивай ОДНИМ
        вопросом-проверкой.
        Не назначай лечение/дозировки; при сомнениях — советуй обсудить
        с врачом.
        """
    ).strip()
    if diabetes_type == "unknown":
        prompt += " Тип диабета не определён — избегай тип-специфичных рекомендаций."
    return _trim(prompt)


def build_user_prompt_step(topic_slug: str, step_idx: int, prev_summary: str | None) -> str:
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


PHOTO_ANALYSIS_PROMPT = (
    "Определи название блюда, вес порции и его пищевую "
    "ценность (белки, жиры, углеводы, калории, хлебные "
    "единицы). Учитывай изображение и текстовое описание, "
    "если они есть. Ответ на русском языке в формате:\n"
    "<название блюда>\n"
    "Вес: <...> г\n"
    "Белки: <...> г\n"
    "Жиры: <...> г\n"
    "Углеводы: <...> г\n"
    "Калории: <...> ккал\n"
    "ХЕ: <...>"
)

REPORT_ANALYSIS_PROMPT_TEMPLATE = (
    "Проанализируй дневник диабета пользователя и предложи краткие рекомендации."
    "\n\nСводка:\n{summary}\n\nОшибки и критические значения:\n{errors}"
    "\n\nДанные по дням:\n{days}\n"
)

LESSONS_V0_PATH = Path(__file__).resolve().parents[5] / "content" / "lessons_v0.json"

with LESSONS_V0_PATH.open(encoding="utf-8") as fp:
    LESSONS_V0_DATA = json.load(fp)

__all__ = [
    "MAX_PROMPT_LEN",
    "disclaimer",
    "SYSTEM_TUTOR_RU",
    "build_explain_step",
    "build_quiz_check",
    "build_feedback",
    "build_system_prompt",
    "build_user_prompt_step",
    "PHOTO_ANALYSIS_PROMPT",
    "REPORT_ANALYSIS_PROMPT_TEMPLATE",
    "LESSONS_V0_PATH",
    "LESSONS_V0_DATA",
]

