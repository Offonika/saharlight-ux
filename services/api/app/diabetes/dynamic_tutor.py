from __future__ import annotations

from collections.abc import Mapping

from openai.types.chat import ChatCompletionMessageParam

from .llm_router import LLMRouter, LLMTask
from .learning_prompts import build_system_prompt, build_user_prompt_step
from .services.gpt_client import create_chat_completion, format_reply


async def _chat(model: str, system: str, user: str, *, max_tokens: int = 350) -> str:
    """Call OpenAI chat completion and format the reply."""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    completion = await create_chat_completion(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=max_tokens,
    )
    content = completion.choices[0].message.content or ""
    return format_reply(content)


async def generate_step_text(
    profile: Mapping[str, str | None],
    topic_slug: str,
    step_idx: int,
    prev_summary: str | None,
) -> str:
    """Generate explanation text for a learning step."""
    model = LLMRouter().choose_model(LLMTask.EXPLAIN_STEP)
    try:
        system = build_system_prompt(profile)
        user = build_user_prompt_step(topic_slug, step_idx, prev_summary)
        return await _chat(model, system, user)
    except RuntimeError:
        return "сервер занят, попробуйте позже"


async def check_user_answer(
    profile: Mapping[str, str | None],
    topic_slug: str,
    user_answer: str,
    last_step_text: str,
    ) -> tuple[bool, str]:
    """Evaluate user's quiz answer and provide feedback.

    The LLM is instructed to classify the answer as ``верно`` (correct),
    ``почти`` or ``неверно``.  To make downstream logic aware of the
    correctness we attempt to parse the returned text and extract a boolean
    flag.  The raw feedback text is returned alongside the flag.
    """
    model = LLMRouter().choose_model(LLMTask.QUIZ_CHECK)
    system = build_system_prompt(profile)
    user = (
        f"Тема: {topic_slug}. Текст предыдущего шага:\n{last_step_text}\n\n"
        f"Ответ пользователя: «{user_answer}». Оцени кратко (верно/почти/неверно), "
        "объясни в 1–2 предложениях и дай мягкий совет, что повторить."
    )

    def _parse_correctness(text: str) -> bool:
        lowered = text.strip().lower()
        if lowered.startswith("неверно") or lowered.startswith("почти"):
            return False
        if lowered.startswith("верно") or lowered.startswith("правильно"):
            return True
        return False

    try:
        reply = await _chat(model, system, user, max_tokens=250)
        return _parse_correctness(reply), reply
    except RuntimeError:
        return False, "сервер занят, попробуйте позже"


__all__ = ["generate_step_text", "check_user_answer"]
