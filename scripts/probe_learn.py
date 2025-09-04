#!/usr/bin/env python3
"""Run through a learning lesson end-to-end.

Example:
    python scripts/probe_learn.py --lesson xe_basics
"""

from __future__ import annotations

# ruff: noqa: E402

import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.curriculum_engine import (
    check_answer,
    next_step,
    start_lesson,
)
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.models_learning import (
    Lesson,
    LessonProgress,
    LessonStep,
    QuizQuestion,
)
from services.api.app.diabetes.services import db, gpt_client


async def run(slug: str) -> int:
    """Return quiz score for the completed lesson ``slug``."""

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)

    await load_lessons(sessionmaker=db.SessionLocal)

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        session.commit()
        lesson = session.query(Lesson).filter_by(slug=slug).one()
        lesson_id = lesson.id
        step_count = session.query(LessonStep).filter_by(lesson_id=lesson_id).count()
        questions = (
            session.query(QuizQuestion)
            .filter_by(lesson_id=lesson_id)
            .order_by(QuizQuestion.id)
            .all()
        )

    async def fake_completion(**_: object) -> str:
        return "text"

    gpt_client.create_learning_chat_completion = fake_completion

    await start_lesson(1, slug)
    for _ in range(step_count):
        await next_step(1, lesson_id)
    await next_step(1, lesson_id)

    for q in questions:
        await check_answer(1, lesson_id, q.correct_option)
        await next_step(1, lesson_id)

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        score = progress.quiz_score
        assert score is not None
    return score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lesson", required=True, help="lesson slug to probe")
    args = parser.parse_args()
    score = asyncio.run(run(args.lesson))
    print(f"Lesson {args.lesson} completed with score {score}")


if __name__ == "__main__":
    main()
