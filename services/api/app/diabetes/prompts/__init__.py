# services/api/app/diabetes/prompts/__init__.py
"""Central storage for GPT prompt templates and instructions (ru-RU)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from textwrap import dedent

# --- Meta ---------------------------------------------------------------------

PROMPT_VERSION = "v0.3"
PROMPT_LANG = "ru-RU"
MAX_PROMPT_LEN = 1_500


def _trim(text: str, limit: int = MAX_PROMPT_LEN) -> str:
    """Ensure *text* does not exceed ``limit`` characters."""
    return (text or "")[:limit]


# --- Common helpers / disclaimers ---------------------------------------------

def disclaimer() -> str:
    """Standard medical warning used across prompts."""
    # Коротко, единообразно: выводим в системном промпте, не дублируем в каждом шаге.
    return "Это не медицинская консультация. Обсудите решения с лечащим врачом."


# Базовый системный промпт (может использоваться в статических сценариях)
SYSTEM_TUTOR_RU = (
    "Ты — репетитор по диабету. "
    "Говори короткими предложениями (2–4). "
    "Сначала спрашивай по теме шага, затем объясняй. "
    "Не давай дозировок и назначений. "
    f"Всегда добавляй предупреждение: '{disclaimer()}'"
)

# Формат безопасного фидбэка при проверке ответов (без новых вопросов)
QUIZ_CHECK_FORMAT_RU = (
    "Проверяешь короткие ответы ученика. НЕ задавай новых вопросов и НЕ используй символ «?». "
    "Верни строго один из форматов:\n"
    "✅ Верно: <1–2 предложения>\n"
    "⚠️ Почти: <1–2 предложения>\n"
    "❌ Неверно: <1–2 предложения>"
)

# Тоны речи по возрастным группам
AGE_TONE: dict[str, str] = {
    "teen": "простым дружелюбным языком",
    "adult": "ясно и по делу",
    "60+": "очень простыми и поддерживающими фразами",
}

# Канонические цели уроков (для динамических шагов)
LESSON_GOALS_RU: dict[str, str] = {
    "xe_basics": "объяснить, что такое ХЕ (~10–12 г углеводов) на простых примерах",
    "healthy-eating": "дать 3 базовых правила питания и один применимый совет",
    "basics-of-diabetes": "кратко: что такое сахар крови и зачем замеры",
    "insulin-usage": "связь углеводов и короткого инсулина на уровне принципов (без доз)",
}

# Алиасы для слугов (совместимость со старыми путями/кнопками)
SLUG_ALIASES: dict[str, str] = {
    "xe": "xe_basics",
    "xe-basics": "xe_basics",
    "healthy": "healthy-eating",
    "diabetes-basics": "basics-of-diabetes",
    "insulin": "insulin-usage",
}


def _canon_slug(slug: str | None) -> str:
    """Map input slug/alias to canonical topic slug."""
    s = (slug or "").strip()
    return SLUG_ALIASES.get(s, s) or "basics-of-diabetes"


# --- Dynamic prompts -----------------------------------------------------------

def build_system_prompt(p: Mapping[str, str | None], task: object | None = None) -> str:
    """Build a system prompt tailored to the user *p* profile."""
    age = (p.get("age_group") or "").strip()
    tone = AGE_TONE.get(age, "ясно и просто")

    diabetes_type = (p.get("diabetes_type") or "unknown").strip() or "unknown"
    therapy = p.get("therapyType", "unknown")
    level = p.get("learning_level", "novice")
    carb_units = p.get("carbUnits", "XE")

    prompt = dedent(
        f"""
        [v={PROMPT_VERSION} lang={PROMPT_LANG}]
        Ты — персональный тьютор по диабету. Подстраивайся под пользователя.
        Профиль: тип диабета={diabetes_type}, терапия={therapy},
        уровень={level}, углеводы={carb_units}. Тон: {tone}.
        Пиши коротко (2–4 предложения). Каждый шаг заканчивай ОДНИМ вопросом-проверкой.
        Не назначай лечение/дозировки. При сомнениях — советуй обсудить с врачом.
        """
    ).strip()

    if diabetes_type == "unknown":
        prompt += " Тип диабета не определён — избегай тип-специфичных рекомендаций."

    # Единый дисклеймер в системном сообщении
    prompt += f" Предупреждение: {disclaimer()}"
    return _trim(prompt)


def build_user_prompt_step(topic_slug: str, step_idx: int, prev_summary: str | None) -> str:
    """Build a user-level prompt for a learning step."""
    slug = _canon_slug(topic_slug)
    goal = LESSON_GOALS_RU.get(slug, "дать понятный и безопасный шаг по теме")
    summary = _trim(prev_summary or "—", 400)

    prompt = (
        f"Тема: {slug}. Цель шага: {goal}. Номер шага: {step_idx}. "
        f"Резюме предыдущего: {summary}. "
        "Сначала объясни, затем задай один вопрос. Ответ не показывай."
    )
    return _trim(prompt)


def build_explain_step(step: str) -> str:
    """Simple explain prompt."""
    return _trim(f"Что ты знаешь о «{step}»? Объясни коротко и понятно.")


def build_quiz_check(question: str, options: list[str]) -> str:
    """Multiple-choice check prompt."""
    opts = "; ".join(options)
    return _trim(f"{question}? Варианты: {opts}. Выбери один.")


def build_feedback(correct: bool, explanation: str) -> str:
    """Short feedback without question marks."""
    prefix = "✅ Верно:" if correct else "❌ Неверно:"
    return _trim(f"{prefix} {explanation}".strip())


# --- Vision / reports ----------------------------------------------------------

PHOTO_ANALYSIS_PROMPT = (
    "Определи название блюда, вес порции и его пищевую ценность (белки, жиры, "
    "углеводы, калории, хлебные единицы). Учитывай изображение и текстовое описание, "
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
    "Проанализируй дневник диабета пользователя и предложи краткие рекомендации.\n\n"
    "Сводка:\n{summary}\n\nОшибки и критические значения:\n{errors}\n\n"
    "Данные по дням:\n{days}\n"
)

# --- Static lessons (optional legacy content) ---------------------------------

LESSONS_V0_PATH = Path(__file__).resolve().parents[5] / "content" / "lessons_v0.json"

try:
    with LESSONS_V0_PATH.open(encoding="utf-8") as fp:
        LESSONS_V0_DATA = json.load(fp)
except FileNotFoundError:
    LESSONS_V0_DATA = {}
except Exception:
    # fail-open: не ломаем импорт, просто оставляем пустые данные
    LESSONS_V0_DATA = {}


__all__ = [
    # meta
    "PROMPT_VERSION",
    "PROMPT_LANG",
    "MAX_PROMPT_LEN",
    # helpers
    "disclaimer",
    "build_system_prompt",
    "build_user_prompt_step",
    "build_explain_step",
    "build_quiz_check",
    "build_feedback",
    "_canon_slug",
    # constants
    "SYSTEM_TUTOR_RU",
    "QUIZ_CHECK_FORMAT_RU",
    "PHOTO_ANALYSIS_PROMPT",
    "REPORT_ANALYSIS_PROMPT_TEMPLATE",
    "LESSONS_V0_PATH",
    "LESSONS_V0_DATA",
    "LESSON_GOALS_RU",
    "AGE_TONE",
    "SLUG_ALIASES",
]
