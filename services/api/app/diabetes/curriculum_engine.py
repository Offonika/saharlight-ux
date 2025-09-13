from __future__ import annotations

import logging
import time
from collections.abc import Mapping

import sqlalchemy as sa
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import settings
from .dynamic_tutor import (
    BUSY_MESSAGE,
    check_user_answer,
    generate_step_text,
    ensure_single_question,
)
from .prompts import (
    SYSTEM_TUTOR_RU,
    build_explain_step,
    build_feedback,
    build_system_prompt,
    disclaimer,
)
from .llm_router import LLMTask
from .metrics import lessons_completed, lessons_started, quiz_avg_score
from .models_learning import Lesson, LessonProgress, LessonStep, QuizQuestion
from .services import db, gpt_client
from .services.repository import commit

logger = logging.getLogger(__name__)


class LessonNotFoundError(Exception):
    """Raised when a lesson with a given slug does not exist."""

    def __init__(self, slug: str) -> None:
        super().__init__(f"lesson not found: {slug}")
        self.slug = slug


class ProgressNotFoundError(Exception):
    """Raised when a user's lesson progress is missing."""

    def __init__(self, user_id: int, lesson_id: int) -> None:
        super().__init__(
            f"progress not found: user_id={user_id}, lesson_id={lesson_id}"
        )
        self.user_id = user_id
        self.lesson_id = lesson_id


async def start_lesson(user_id: int, lesson_slug: str) -> LessonProgress:
    """Start or reset a lesson for a user and return progress."""

    def _start(session: Session) -> LessonProgress:
        lesson = session.execute(
            sa.select(Lesson).filter_by(slug=lesson_slug)
        ).scalar_one_or_none()
        if lesson is None:
            raise LessonNotFoundError(lesson_slug)
        progress = session.execute(
            sa.select(LessonProgress).filter_by(user_id=user_id, lesson_id=lesson.id)
        ).scalar_one_or_none()
        if progress is None:
            progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson.id,
                current_step=0,
                current_question=0,
                completed=False,
                quiz_score=None,
            )
            session.add(progress)
        else:
            progress.current_step = 0
            progress.current_question = 0
            progress.completed = False
            progress.quiz_score = None
        commit(session)
        session.refresh(progress)
        return progress

    progress = await db.run_db(_start)
    lessons_started.inc()
    return progress


async def next_step(
    user_id: int,
    lesson_id: int,
    profile: Mapping[str, str | None],
    prev_summary: str | None = None,
) -> tuple[str | None, bool]:
    """Advance the lesson and return the next piece of content.

    Behaviour is determined by ``settings.learning_content_mode``:

    * "dynamic" - generate step text on the fly.
    * "static" - use predefined steps and quiz questions from the database.
    """

    if settings.learning_content_mode == "dynamic":

        def _get_progress(session: Session) -> tuple[int, str]:
            progress = session.execute(
                sa.select(LessonProgress).filter_by(
                    user_id=user_id, lesson_id=lesson_id
                )
            ).scalar_one_or_none()
            if progress is None:
                raise ProgressNotFoundError(user_id, lesson_id)
            lesson = session.execute(
                sa.select(Lesson).filter_by(id=lesson_id)
            ).scalar_one_or_none()
            if lesson is None:
                raise LessonNotFoundError(str(lesson_id))
            return progress.current_step, lesson.slug

        current_step, slug = await db.run_db(_get_progress)
        step_idx = current_step + 1
        try:
            text = await generate_step_text(
                profile, slug, step_idx, prev_summary, user_id=user_id
            )
        except OpenAIError:
            logger.exception(
                "openai error during dynamic step generation",
                extra={"lesson": slug, "step": step_idx},
            )
            return BUSY_MESSAGE, False
        except SQLAlchemyError:
            logger.exception(
                "database error during dynamic step generation",
                extra={"lesson": slug, "step": step_idx},
            )
            raise
        if text == BUSY_MESSAGE:
            return BUSY_MESSAGE, False
        text = ensure_single_question(text)

        def _advance(session: Session) -> None:
            progress = session.execute(
                sa.select(LessonProgress).filter_by(
                    user_id=user_id, lesson_id=lesson_id
                )
            ).scalar_one()
            progress.current_step = step_idx
            commit(session)

        await db.run_db(_advance)
        if step_idx == 1:
            return f"{disclaimer()}\n\n{text}", False
        return text, False

    def _advance_static(
        session: Session,
    ) -> tuple[str | None, str | None, bool, bool, int, bool, str]:
        progress = session.execute(
            sa.select(LessonProgress).filter_by(user_id=user_id, lesson_id=lesson_id)
        ).scalar_one()
        lesson = session.execute(sa.select(Lesson).filter_by(id=lesson_id)).scalar_one()
        steps = session.scalars(
            sa.select(LessonStep)
            .filter_by(lesson_id=lesson_id)
            .order_by(LessonStep.step_order)
        ).all()
        if progress.current_step < len(steps):
            step = steps[progress.current_step]
            first_step = progress.current_step == 0
            progress.current_step += 1
            step_idx = progress.current_step
            commit(session)
            return step.content, None, first_step, False, step_idx, False, lesson.slug
        questions = session.scalars(
            sa.select(QuizQuestion)
            .filter_by(lesson_id=lesson_id)
            .order_by(QuizQuestion.id)
        ).all()
        if progress.current_question < len(questions):
            q = questions[progress.current_question]
            first_question = progress.current_question == 0
            opts = "\n".join(
                f"{idx}. {opt}" for idx, opt in enumerate(q.options, start=1)
            )
            return (
                None,
                f"{q.question}\n{opts}",
                False,
                first_question,
                progress.current_step,
                False,
                lesson.slug,
            )
        if not progress.completed:
            progress.completed = True
            commit(session)
        return None, None, False, False, progress.current_step, True, lesson.slug

    (
        step_content,
        question_text,
        first_step,
        first_question,
        step_idx,
        completed,
        slug,
    ) = await db.run_db(_advance_static)
    if step_content is not None and step_idx is not None:
        start = time.monotonic()
        try:
            text = await gpt_client.create_learning_chat_completion(
                task=LLMTask.EXPLAIN_STEP,
                messages=[
                    {"role": "system", "content": SYSTEM_TUTOR_RU},
                    {"role": "user", "content": build_explain_step(step_content)},
                ],
                user_id=user_id,
            )
        except OpenAIError:
            logger.exception(
                "openai error during learning chat completion",
                extra={
                    "user_id": user_id,
                    "lesson_id": lesson_id,
                    "step": step_idx,
                },
            )
            return BUSY_MESSAGE, completed
        except SQLAlchemyError:
            logger.exception(
                "database error during learning chat completion",
                extra={
                    "user_id": user_id,
                    "lesson_id": lesson_id,
                    "step": step_idx,
                },
            )
            raise
        latency = time.monotonic() - start
        logger.info(
            "lesson_step",
            extra={
                "user_id": user_id,
                "lesson_id": lesson_id,
                "step": step_idx,
                "latency": latency,
            },
        )
        text = ensure_single_question(text)
        if first_step:
            return f"{disclaimer()}\n\n{text}", completed
        return text, completed
    if question_text is not None:
        question_text = ensure_single_question(question_text)
        if first_question:
            return f"{disclaimer()}\n\n{question_text}", completed
        return question_text, completed
    return None, completed


async def check_answer(
    user_id: int,
    lesson_id: int,
    profile: Mapping[str, str | None],
    answer: int | str,
    last_step_text: str | None = None,
) -> tuple[bool, str]:
    """Check user's answer using the given profile and return feedback."""

    if settings.learning_content_mode == "dynamic":

        def _get_slug(session: Session) -> str:
            lesson = session.execute(
                sa.select(Lesson).filter_by(id=lesson_id)
            ).scalar_one()
            return lesson.slug

        slug = await db.run_db(_get_slug)
        correct, feedback = await check_user_answer(
            profile, slug, str(answer), last_step_text or "", user_id=user_id
        )
        feedback = feedback.strip()
        return correct, feedback

    try:
        answer_index = int(answer) - 1
    except (TypeError, ValueError):
        return False, "Пожалуйста, выберите номер варианта"

    def _check(session: Session) -> tuple[bool, str, int, bool, int | None]:
        progress = session.execute(
            sa.select(LessonProgress).filter_by(user_id=user_id, lesson_id=lesson_id)
        ).scalar_one()
        questions = session.scalars(
            sa.select(QuizQuestion)
            .filter_by(lesson_id=lesson_id)
            .order_by(QuizQuestion.id)
        ).all()
        question = questions[progress.current_question]
        correct = answer_index == question.correct_option
        explanation = question.options[question.correct_option]
        question_idx = progress.current_question
        score = progress.quiz_score or 0
        if correct:
            score += 1
        progress.quiz_score = score
        progress.current_question += 1
        if progress.current_question >= len(questions):
            progress.completed = True
            progress.quiz_score = int(100 * score / len(questions))
        completed = progress.completed
        final_score = progress.quiz_score
        commit(session)
        return correct, explanation, question_idx, completed, final_score

    correct, explanation, question_idx, completed, final_score = await db.run_db(_check)
    if completed and final_score is not None:
        lessons_completed.inc()
        quiz_avg_score.observe(float(final_score))
    start = time.monotonic()
    message = await gpt_client.create_learning_chat_completion(
        task=LLMTask.QUIZ_CHECK,
        messages=[
            {
                "role": "system",
                "content": build_system_prompt(profile, task=LLMTask.QUIZ_CHECK),
            },
            {"role": "user", "content": build_feedback(correct, explanation)},
        ],
        user_id=user_id,
    )
    latency = time.monotonic() - start
    logger.info(
        "lesson_step",
        extra={
            "user_id": user_id,
            "lesson_id": lesson_id,
            "step": question_idx,
            "latency": latency,
        },
    )
    return correct, message


__all__ = ["start_lesson", "next_step", "check_answer"]
