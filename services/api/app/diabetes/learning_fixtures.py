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

import json
import logging
from pathlib import Path
from typing import TypedDict, cast

from sqlalchemy.orm import Session

from .models_learning import Lesson, QuizQuestion
from .services.db import SessionLocal, SessionMaker, run_db
from .services.repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = ["load_lessons"]


class QuizDict(TypedDict):
    question: str
    options: list[str]
    answer: int


class LessonDict(TypedDict):
    title: str
    steps: list[str]
    quiz: list[QuizDict]


DEFAULT_CONTENT_FILE = Path(__file__).parent / "content" / "lessons_v0.json"


async def load_lessons(
    content_path: Path | str = DEFAULT_CONTENT_FILE,
    *,
    sessionmaker: SessionMaker[Session] = SessionLocal,
) -> None:
    """Load lessons and quiz questions from ``content_path`` into the database."""

    path = Path(content_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    lessons = cast(list[LessonDict], raw)

    def _load(session: Session) -> None:
        for item in lessons:
            lesson = Lesson(
                title=item["title"],
                content="\n".join(item["steps"]),
                is_active=True,
            )
            session.add(lesson)
            session.flush()
            for q in item["quiz"]:
                question = QuizQuestion(
                    lesson_id=lesson.id,
                    question=q["question"],
                    options=q["options"],
                    correct_option=q["answer"],
                )
                session.add(question)
        try:
            commit(session)
        except CommitError:
            logger.exception("Failed to load lessons from %s", path)
            raise

    await run_db(_load, sessionmaker=sessionmaker)
