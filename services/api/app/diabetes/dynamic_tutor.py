from __future__ import annotations

from collections.abc import Mapping

from openai.types.chat import ChatCompletionMessageParam

from .llm_router import LLMTask
from .learning_prompts import build_system_prompt, build_user_prompt_step
from .services.gpt_client import create_learning_chat_completion


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
        system = build_system_prompt(profile)
        user = build_user_prompt_step(topic_slug, step_idx, prev_summary)
        return await _chat(LLMTask.EXPLAIN_STEP, system, user)
    except RuntimeError:
        return "сервер занят, попробуйте позже"


async def check_user_answer(
    profile: Mapping[str, str | None],
    topic_slug: str,
    user_answer: str,
    last_step_text: str,
) -> tuple[bool, str]:
    """Evaluate user's quiz answer and provide feedback.

    Returns a tuple ``(correct, feedback)`` where ``correct`` is ``True`` if the
    LLM judged the answer as correct. The feedback message is returned as-is
    from the model.
    """
    system = build_system_prompt(profile)
    user = (
        f"Тема: {topic_slug}. Текст предыдущего шага:\n{last_step_text}\n\n"
        f"Ответ пользователя: «{user_answer}». Оцени кратко (верно/почти/неверно), "
        "объясни в 1–2 предложениях и дай мягкий совет, что повторить."
    )
    try:
        feedback = await _chat(LLMTask.QUIZ_CHECK, system, user, max_tokens=250)
    except RuntimeError:
        return False, "сервер занят, попробуйте позже"

    first = feedback.split(maxsplit=1)[0].strip(".,!?:;\"'«»").lower()
    correct = first in {"верно", "правильно"}
    return correct, feedback


__all__ = ["generate_step_text", "check_user_answer"]
