"""Command-line utility to walk through learning lessons."""

from __future__ import annotations

import argparse
import asyncio
import os

import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.api.app import config
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.curriculum_engine import (
    LessonNotFoundError,
    ProgressNotFoundError,
)
from services.api.app.diabetes.dynamic_tutor import BUSY_MESSAGE
from services.api.app.diabetes.models_learning import (
    LessonProgress,
    LessonStep,
    QuizQuestion,
)
from services.api.app.diabetes.services import db


async def _fetch_lesson_data(
    lesson_id: int,
) -> tuple[int, list[QuizQuestion]]:
    """Return number of steps and list of questions for a lesson."""

    def _query(session: Session) -> tuple[int, list[QuizQuestion]]:
        step_count = session.execute(
            sa.select(sa.func.count())
            .select_from(LessonStep)
            .filter_by(lesson_id=lesson_id)
        ).scalar_one()
        questions = session.scalars(
            sa.select(QuizQuestion)
            .filter_by(lesson_id=lesson_id)
            .order_by(QuizQuestion.id)
        ).all()
        return step_count, list(questions)

    return await db.run_db(_query)


async def _get_progress(user_id: int, lesson_id: int) -> LessonProgress:
    """Fetch lesson progress for a user."""

    def _query(session: Session) -> LessonProgress:
        return session.execute(
            sa.select(LessonProgress).filter_by(user_id=user_id, lesson_id=lesson_id)
        ).scalar_one()

    return await db.run_db(_query)


async def main(user_id: int, lesson_slug: str) -> None:
    os.environ.setdefault("LEARNING_MODEL_DEFAULT", "gpt-4o-mini")
    os.environ.setdefault("LEARNING_PROMPT_CACHE", "1")
    config.reload_settings()

    progress = await curriculum_engine.start_lesson(user_id, lesson_slug)
    lesson_id = progress.lesson_id

    step_total, questions = await _fetch_lesson_data(lesson_id)

    steps_done = 0
    quiz_index = 0

    while True:
        try:
            text, completed = await curriculum_engine.next_step(user_id, lesson_id, {})
        except (LessonNotFoundError, ProgressNotFoundError) as exc:
            print(str(exc))
            break
        if text == BUSY_MESSAGE:
            print(text)
            break
        if text is None and completed:
            break
        print(text)
        if steps_done >= step_total and quiz_index < len(questions):
            answer = questions[quiz_index].correct_option
            _, feedback = await curriculum_engine.check_answer(
                user_id, lesson_id, {}, answer
            )
            print(feedback)
            quiz_index += 1
        else:
            steps_done += 1

    final_progress = await _get_progress(user_id, lesson_id)
    print(f"Final score: {final_progress.quiz_score}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probe learning lessons")
    parser.add_argument("--user", type=int, required=True, help="User identifier")
    parser.add_argument("--lesson", required=True, help="Lesson slug to start")
    args = parser.parse_args()
    asyncio.run(main(args.user, args.lesson))
