from __future__ import annotations

import logging
import re
from typing import Mapping

import httpx
from openai import OpenAIError
from openai.types.chat import ChatCompletionMessageParam

from .prompts import build_system_prompt, build_user_prompt_step
from .llm_router import LLMTask
from .services.gpt_client import create_learning_chat_completion

logger = logging.getLogger(__name__)

BUSY_MESSAGE = "сервер занят, попробуйте позже"


_TAGS_RE = re.compile(r"<[^>]+>")
_SAFE_RE = re.compile(r"[^0-9A-Za-zА-Яа-яёЁ.,!?;:()\-\s✅⚠️❌'\"]")

_MAX_FEEDBACK_CHARS = 400
_MAX_FEEDBACK_SENTENCES = 2

_AFFIRMATIVE_WORDS: set[str] = {
    "да",
    "ага",
    "угу",
    "есть",
    "ок",
    "окей",
    "okay",
    "ok",
    "yes",
    "yep",
    "yeah",
    "sure",
    "конечно",
}


def is_affirmative(text: str) -> bool:
    """Return ``True`` if ``text`` looks like an affirmative reply."""

    cleaned = re.sub(r"[^a-zа-яё\s]+", " ", text.lower())
    return any(word in _AFFIRMATIVE_WORDS for word in cleaned.split())


def sanitize_feedback(text: str) -> str:
    """Clean LLM feedback and enforce basic formatting rules."""

    cleaned = _TAGS_RE.sub("", text)
    cleaned = _SAFE_RE.sub(" ", cleaned)

    sentences = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    sentences = [s.replace("?", "").strip() for s in sentences if s]
    cleaned = " ".join(sentences[:_MAX_FEEDBACK_SENTENCES])
    cleaned = cleaned[:_MAX_FEEDBACK_CHARS]
    return " ".join(cleaned.split())


def ensure_single_question(text: str) -> str:
    """Leave only the first question mark in the given text."""

    idx = text.find("?")
    if idx == -1:
        return text
    return text[: idx + 1] + text[idx + 1 :].replace("?", "")


async def _chat(task: LLMTask, system: str, user: str, *, max_tokens: int = 350) -> str:
    """Call OpenAI chat completion and return the formatted reply."""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return await create_learning_chat_completion(
        task=task,
        messages=messages,
        temperature=0.4,
        max_tokens=max_tokens,
    )


async def generate_step_text(
    profile: Mapping[str, str | None],
    topic_slug: str,
    step_idx: int,
    prev_summary: str | None,
) -> str:
    """Generate explanation text for a learning step."""
    try:
        system = build_system_prompt(profile, task=LLMTask.EXPLAIN_STEP)
        user = build_user_prompt_step(topic_slug, step_idx, prev_summary)
        return await _chat(LLMTask.EXPLAIN_STEP, system, user)
    except (OpenAIError, httpx.HTTPError, RuntimeError):
        logger.exception(
            "failed to generate step", extra={"topic": topic_slug, "step": step_idx}
        )
        return BUSY_MESSAGE


async def check_user_answer(
    profile: Mapping[str, str | None],
    topic_slug: str,
    user_answer: str,
    last_step_text: str,
) -> tuple[bool, str]:
    """Evaluate user's quiz answer and provide feedback.

    The function returns a tuple ``(correct, feedback)``. If ``user_answer`` is
    an explicit confirmation like "да" or "yes", the result is immediately
    ``(True, "✅ отлично!")`` without calling the LLM. Otherwise, the LLM is
    asked to judge the answer and provide feedback.
    """
    if is_affirmative(user_answer):
        return True, "✅ отлично!"

    system = build_system_prompt(profile, task=LLMTask.QUIZ_CHECK)
    user = (
        f"Тема: {topic_slug}. Текст предыдущего шага:\n{last_step_text}\n\n"
        f"Ответ пользователя: «{user_answer}». Оцени кратко (верно/почти/неверно), "
        "объясни в 1–2 предложениях и дай мягкий совет, что повторить."
    )
    try:
        raw_feedback = await _chat(LLMTask.QUIZ_CHECK, system, user, max_tokens=250)
    except (OpenAIError, httpx.HTTPError, RuntimeError):
        logger.exception(
            "failed to check answer",
            extra={"topic": topic_slug, "answer": user_answer},
        )
        return False, BUSY_MESSAGE

    feedback = sanitize_feedback(raw_feedback)
    if not feedback:
        logger.warning(
            "empty feedback",
            extra={"topic": topic_slug, "answer": user_answer},
        )
        return False, BUSY_MESSAGE

    stripped = feedback.lstrip()
    correct = stripped.startswith("✅")
    return correct, feedback


__all__ = [
    "generate_step_text",
    "check_user_answer",
    "is_affirmative",
    "sanitize_feedback",
    "ensure_single_question",
    "BUSY_MESSAGE",
]
