from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from .learning_prompts import SYSTEM_TUTOR_RU, build_explain_step, build_feedback
from .llm_router import LLMTask
from .models_learning import Lesson, LessonProgress, QuizQuestion
from .services.db import SessionLocal, run_db
from .services.gpt_client import create_learning_chat_completion
from .services.repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = ["start_lesson", "next_step", "check_answer"]


async def start_lesson(user_id: int, lesson_slug: str) -> LessonProgress:
    """Start or reset a lesson for *user_id*.

    Parameters
    ----------
    user_id: int
        Telegram identifier of the user.
    lesson_slug: str
        Slug of the lesson to start.
    """

    def _start(session: Session) -> LessonProgress:
        lesson = session.query(Lesson).filter_by(slug=lesson_slug).one()
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=user_id, lesson_id=lesson.id)
            .one_or_none()
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
            logger.exception(
                "Failed to start lesson %s for user %s", lesson_slug, user_id
            )
            raise
        session.refresh(progress)
        return progress

    return await run_db(_start, sessionmaker=SessionLocal)


async def next_step(user_id: int, lesson_id: int) -> str | None:
    """Return the next lesson step or quiz question for the user.

    Parameters
    ----------
    user_id: int
        Telegram identifier of the user.
    lesson_id: int
        Identifier of the lesson.
    """

    def _load(session: Session) -> tuple[LessonProgress, Lesson]:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=user_id, lesson_id=lesson_id)
            .one()
        )
        lesson = session.get(Lesson, lesson_id)
        assert lesson is not None
        # Preload relationships to avoid DetachedInstanceError
        _ = lesson.steps, lesson.questions
        return progress, lesson

    progress, lesson = await run_db(_load, sessionmaker=SessionLocal)
    assert lesson is not None

    if progress.current_step < len(lesson.steps):
        step = lesson.steps[progress.current_step]
        completion = await create_learning_chat_completion(
            task=LLMTask.EXPLAIN_STEP,
            messages=[
                {"role": "system", "content": SYSTEM_TUTOR_RU},
                {"role": "user", "content": build_explain_step(step.content)},
            ],
        )
        text = completion.choices[0].message.content or ""

        def _update(session: Session) -> None:
            prog = session.get(LessonProgress, progress.id)
            assert prog is not None
            prog.current_step += 1
            try:
                commit(session)
            except CommitError:
                logger.exception(
                    "Failed to update step %s for user %s", progress.id, user_id
                )
                raise

        await run_db(_update, sessionmaker=SessionLocal)
        return text

    if progress.current_question < len(lesson.questions):
        question = lesson.questions[progress.current_question]
        opts = "\n".join(
            f"{idx + 1}. {opt}" for idx, opt in enumerate(question.options)
        )
        return f"{question.question}\n{opts}".strip()

    return None


async def check_answer(
    user_id: int, lesson_id: int, answer_index: int
) -> tuple[bool, str]:
    """Check user's quiz answer and provide feedback.

    Parameters
    ----------
    user_id: int
        Telegram identifier of the user.
    lesson_id: int
        Identifier of the lesson.
    answer_index: int
        Index of the chosen answer.
    """

    def _load(session: Session) -> tuple[LessonProgress, QuizQuestion]:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=user_id, lesson_id=lesson_id)
            .one()
        )
        question = progress.lesson.questions[progress.current_question]
        return progress, question

    progress, question = await run_db(_load, sessionmaker=SessionLocal)
    correct = answer_index == question.correct_option
    explanation = question.options[question.correct_option]
    completion = await create_learning_chat_completion(
        task=LLMTask.QUIZ_CHECK,
        messages=[
            {"role": "system", "content": SYSTEM_TUTOR_RU},
            {"role": "user", "content": build_feedback(correct, explanation)},
        ],
    )
    text = completion.choices[0].message.content or ""

    def _update(session: Session) -> None:
        prog = session.get(LessonProgress, progress.id)
        assert prog is not None
        questions = prog.lesson.questions  # preload
        prog.current_question += 1
        if prog.quiz_score is None:
            prog.quiz_score = 0
        if correct:
            prog.quiz_score += 1
        if prog.current_question >= len(questions):
            prog.completed = True
        try:
            commit(session)
        except CommitError:
            logger.exception(
                "Failed to commit quiz answer for user %s lesson %s", user_id, lesson_id
            )
            raise

    await run_db(_update, sessionmaker=SessionLocal)
    return correct, text
