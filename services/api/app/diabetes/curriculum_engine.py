from __future__ import annotations

import logging

from openai.types.chat import ChatCompletionMessageParam

import sqlalchemy as sa
from sqlalchemy.orm import Session

from .learning_prompts import SYSTEM_TUTOR_RU, build_explain_step, build_feedback
from .llm_router import LLMTask
from .models_learning import Lesson, LessonProgress
from .services.db import SessionLocal, run_db
from .services.gpt_client import create_learning_chat_completion
from .services.repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = ["start_lesson", "next_step", "check_answer"]


async def start_lesson(user_id: int, lesson_slug: str) -> LessonProgress:
    """Start or reset a lesson for *user_id* by its *lesson_slug*."""

    def _start(session: Session) -> LessonProgress:
        slug_attr = getattr(Lesson, "slug", Lesson.title)
        lesson = session.scalar(
            sa.select(Lesson).where(slug_attr == lesson_slug)
        )
        if lesson is None:
            raise ValueError(f"Lesson not found: {lesson_slug}")

        progress = session.scalar(
            sa.select(LessonProgress)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson.id,
            )
        )
        if progress is None:
            progress = LessonProgress(user_id=user_id, lesson_id=lesson.id)
            session.add(progress)

        progress.current_step = 0
        progress.current_question = 0
        progress.completed = False
        progress.quiz_score = None
        try:
            commit(session)
        except CommitError:
            logger.exception("Failed to start lesson %s for %s", lesson_slug, user_id)
            raise
        return progress

    return await run_db(_start, sessionmaker=SessionLocal)


async def next_step(user_id: int, lesson_id: int) -> str | None:
    """Advance to the next step or quiz question and return generated text."""

    def _load(session: Session) -> tuple[LessonProgress, list[str], list[str], list[list[str]]]:
        progress = session.scalar(
            sa.select(LessonProgress)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id,
            )
        )
        if progress is None:
            raise ValueError("Progress not found")
        lesson = progress.lesson
        steps = [s.content for s in lesson.steps]
        questions = [q.question for q in lesson.questions]
        options = [list(q.options) for q in lesson.questions]
        return progress, steps, questions, options

    progress, steps, questions, options = await run_db(_load, sessionmaker=SessionLocal)

    if progress.current_step < len(steps):
        step_text = steps[progress.current_step]
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_TUTOR_RU},
            {"role": "user", "content": build_explain_step(step_text)},
        ]
        completion = await create_learning_chat_completion(
            task=LLMTask.EXPLAIN_STEP,
            messages=messages,
        )
        reply = completion.choices[0].message.content or ""

        def _advance(session: Session) -> None:
            prog = session.get(LessonProgress, progress.id)
            if prog is None:
                return
            prog.current_step += 1
            try:
                commit(session)
            except CommitError:
                logger.exception("Failed to commit progress step for %s", user_id)
                raise

        await run_db(_advance, sessionmaker=SessionLocal)
        return reply

    if progress.current_question < len(questions):
        q = questions[progress.current_question]
        opts = options[progress.current_question]
        opts_text = "\n".join(f"{idx}. {opt}" for idx, opt in enumerate(opts))
        return f"{q}\n{opts_text}".strip()
    return None


async def check_answer(
    user_id: int, lesson_id: int, answer_index: int
) -> tuple[bool, str]:
    """Validate an answer and return a tuple ``(is_correct, feedback)``."""

    def _load(session: Session) -> tuple[LessonProgress, str, list[str], int, int]:
        progress = session.scalar(
            sa.select(LessonProgress)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id,
            )
        )
        if progress is None:
            raise ValueError("Progress not found")
        question = progress.lesson.questions[progress.current_question]
        total = len(progress.lesson.questions)
        return progress, question.question, list(question.options), question.correct_option, total

    progress, question_text, opts, correct_option, total_questions = await run_db(
        _load, sessionmaker=SessionLocal
    )

    is_correct = answer_index == correct_option
    explanation = opts[correct_option]
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_TUTOR_RU},
        {"role": "user", "content": build_feedback(is_correct, explanation)},
    ]
    completion = await create_learning_chat_completion(
        task=LLMTask.QUIZ_CHECK,
        messages=messages,
    )
    feedback = completion.choices[0].message.content or ""

    def _update(session: Session) -> None:
        prog = session.get(LessonProgress, progress.id)
        if prog is None:
            return
        if is_correct:
            prog.quiz_score = (prog.quiz_score or 0) + 1
        prog.current_question += 1
        if prog.current_question >= total_questions:
            prog.completed = True
        try:
            commit(session)
        except CommitError:
            logger.exception("Failed to commit quiz answer for %s", user_id)
            raise

    await run_db(_update, sessionmaker=SessionLocal)
    return is_correct, feedback
