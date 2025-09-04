from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

from .models_learning import Lesson, QuizQuestion
from .services import db


class QuizDict(TypedDict):
    question: str
    options: list[str]
    correct_option: int


class LessonDict(TypedDict):
    title: str
    steps: list[str]
    quiz: list[QuizDict]


def load(path: Path) -> None:
    """Load lessons and quizzes from a JSON file."""
    raw = json.loads(path.read_text())
    data = cast(list[LessonDict], raw)
    with db.SessionLocal() as session:
        for entry in data:
            content = "\n".join(entry["steps"])
            lesson = Lesson(title=entry["title"], content=content)
            session.add(lesson)
            session.flush()
            for q in entry["quiz"]:
                question = QuizQuestion(
                    lesson_id=lesson.id,
                    question=q["question"],
                    options=q["options"],
                    correct_option=q["correct_option"],
                )
                session.add(question)
        session.commit()
