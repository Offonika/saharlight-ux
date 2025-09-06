from __future__ import annotations

from collections.abc import Mapping

from openai.types.chat import ChatCompletionMessageParam
from sqlalchemy.orm import Session

from .llm_router import LLMRouter, LLMTask
from .learning_prompts import build_system_prompt, build_user_prompt_step
from .models_learning import LessonLog
from .services.db import SessionLocal, run_db
from .services.gpt_client import create_chat_completion, format_reply
from .services.repository import commit


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


async def log_lesson_turn(
    telegram_id: int,
    topic_slug: str,
    role: str,
    step_idx: int,
    content: str,
) -> None:
    """Persist a lesson dialog turn to the database."""

    def _log(session: Session) -> None:
        entry = LessonLog(
            telegram_id=telegram_id,
            topic_slug=topic_slug,
            role=role,
            step_idx=step_idx,
            content=content,
        )
        session.add(entry)
        commit(session)

    await run_db(_log, sessionmaker=SessionLocal)


async def generate_step_text(
    telegram_id: int,
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
        text = await _chat(model, system, user)
        await log_lesson_turn(telegram_id, topic_slug, "assistant", step_idx, text)
        return text
    except RuntimeError:
        return "сервер занят, попробуйте позже"


async def check_user_answer(
    telegram_id: int,
    profile: Mapping[str, str | None],
    topic_slug: str,
    step_idx: int,
    user_answer: str,
    last_step_text: str,
) -> str:
    """Evaluate user's quiz answer and provide feedback."""
    model = LLMRouter().choose_model(LLMTask.QUIZ_CHECK)
    system = build_system_prompt(profile)
    user = (
        f"Тема: {topic_slug}. Текст предыдущего шага:\n{last_step_text}\n\n"
        f"Ответ пользователя: «{user_answer}». Оцени кратко (верно/почти/неверно), "
        "объясни в 1–2 предложениях и дай мягкий совет, что повторить."
    )
    try:
        feedback = await _chat(model, system, user, max_tokens=250)
        await log_lesson_turn(telegram_id, topic_slug, "assistant", step_idx, feedback)
        return feedback
    except RuntimeError:
        return "сервер занят, попробуйте позже"


__all__ = ["generate_step_text", "check_user_answer", "log_lesson_turn"]
