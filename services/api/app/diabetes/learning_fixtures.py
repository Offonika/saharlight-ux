"""Utility to load learning content fixtures into the database.

Usage
-----
>>> import asyncio
>>> from services.api.app.diabetes.learning_fixtures import load_lessons
>>> asyncio.run(load_lessons())

This reads the JSON file at ``content/lessons_v0.json`` and inserts
``Lesson`` and ``QuizQuestion`` records using
:mod:`services.api.app.diabetes.services.db`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
import re

import sqlalchemy as sa
from pydantic import BaseModel, TypeAdapter
from sqlalchemy.orm import Session

from .models_learning import Lesson, LessonProgress, LessonStep, QuizQuestion
from .services.db import SessionLocal, SessionMaker, run_db
from .services.repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = ["load_lessons", "reset_lessons"]


class QuizModel(BaseModel):
    question: str
    options: list[str]
    answer: int


class LessonModel(BaseModel):
    slug: str | None = None
    title: str
    steps: list[str]
    quiz: list[QuizModel]


LESSON_LIST = TypeAdapter(list[LessonModel])


DEFAULT_CONTENT_FILE = Path(__file__).resolve().parents[4] / "content" / "lessons_v0.json"


async def load_lessons(
    content_path: Path | str = DEFAULT_CONTENT_FILE,
    *,
    sessionmaker: SessionMaker[Session] = SessionLocal,
) -> None:
    """Load lessons and quiz questions from ``content_path`` into the database."""

    path = Path(content_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    lessons = LESSON_LIST.validate_python(raw)

    def _load(session: Session) -> None:
        for item in lessons:
            slug = item.slug or re.sub(r"[^a-z0-9]+", "-", item.title.lower()).strip("-")
            lesson = Lesson(
                slug=slug,
                title=item.title,
                content="\n".join(item.steps),
                is_active=True,
            )
            session.add(lesson)
            session.flush()
            for idx, step in enumerate(item.steps, start=1):
                session.add(
                    LessonStep(lesson_id=lesson.id, step_order=idx, content=step)
                )
            for q in item.quiz:
                session.add(
                    QuizQuestion(
                        lesson_id=lesson.id,
                        question=q.question,
                        options=q.options,
                        correct_option=q.answer,
                    )
                )
        try:
            commit(session)
        except CommitError:
            logger.exception("Failed to load lessons from %s", path)
            raise

    await run_db(_load, sessionmaker=sessionmaker)


async def reset_lessons(*, sessionmaker: SessionMaker[Session] = SessionLocal) -> None:
    """Remove all lessons and related data."""

    def _reset(session: Session) -> None:
        session.execute(sa.delete(LessonProgress))
        session.execute(sa.delete(QuizQuestion))
        session.execute(sa.delete(LessonStep))
        session.execute(sa.delete(Lesson))
        commit(session)

    await run_db(_reset, sessionmaker=sessionmaker)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load lesson fixtures")
    parser.add_argument("path", nargs="?", default=DEFAULT_CONTENT_FILE)
    parser.add_argument(
        "--reset", action="store_true", help="Clear existing lessons before loading"
    )
    return parser


async def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    if args.reset:
        await reset_lessons()
    await load_lessons(args.path)


if __name__ == "__main__":  # pragma: no cover - CLI utility
    asyncio.run(main())
