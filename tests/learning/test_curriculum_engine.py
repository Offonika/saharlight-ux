from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.models_learning import Lesson, LessonStep, QuizQuestion, LessonProgress
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.content = text


class DummyChoice:
    def __init__(self, text: str) -> None:
        self.message = DummyMessage(text)


class DummyCompletion:
    def __init__(self, text: str) -> None:
        self.choices = [DummyChoice(text)]


@pytest.fixture()
def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(curriculum_engine, "SessionLocal", SessionLocal, raising=False)
    yield SessionLocal
    db.dispose_engine(engine)


def _add_lesson(session: Session) -> int:
    lesson = Lesson(title="intro", content="step one", is_active=True)
    session.add(lesson)
    session.flush()
    session.add(LessonStep(lesson_id=lesson.id, step_order=1, content="step one"))
    session.add(
        QuizQuestion(
            lesson_id=lesson.id,
            question="Q?",
            options=["A", "B"],
            correct_option=0,
        )
    )
    session.commit()
    return lesson.id


@pytest.mark.asyncio()
async def test_start_lesson_resets_progress(setup_db: sessionmaker[Session]) -> None:
    with setup_db() as session:
        _add_lesson(session)
    await curriculum_engine.start_lesson(1, "intro")
    with setup_db() as session:
        prog = session.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == 1,
                LessonProgress.lesson_id == 1,
            )
        ).scalar_one()
        assert prog.current_step == 0
        prog.current_step = 5
        prog.current_question = 3
        prog.completed = True
        prog.quiz_score = 2
        session.commit()
    await curriculum_engine.start_lesson(1, "intro")
    with setup_db() as session:
        prog = session.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == 1,
                LessonProgress.lesson_id == 1,
            )
        ).scalar_one()
        assert prog.current_step == 0
        assert prog.current_question == 0
        assert prog.quiz_score is None
        assert not prog.completed


@pytest.mark.asyncio()
async def test_next_step_and_question_flow(setup_db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> None:
    with setup_db() as session:
        lesson_id = _add_lesson(session)
    captured: list[tuple[str, list[dict[str, str]]]] = []

    async def fake_completion(*, task: curriculum_engine.LLMTask, messages: list[dict[str, str]], **kwargs: object) -> DummyCompletion:  # type: ignore[override]
        captured.append((task.value, messages))
        return DummyCompletion("resp")

    monkeypatch.setattr(curriculum_engine, "create_learning_chat_completion", fake_completion)

    await curriculum_engine.start_lesson(1, "intro")
    text = await curriculum_engine.next_step(1, lesson_id)
    assert text == "resp"
    with setup_db() as session:
        prog = session.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == 1,
                LessonProgress.lesson_id == lesson_id,
            )
        ).scalar_one()
        assert prog.current_step == 1
    text = await curriculum_engine.next_step(1, lesson_id)
    assert "Q?" in text
    assert "0. A" in text
    assert len(captured) == 1


@pytest.mark.asyncio()
async def test_check_answer_updates_progress(setup_db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> None:
    with setup_db() as session:
        lesson_id = _add_lesson(session)
    await curriculum_engine.start_lesson(1, "intro")
    async def fake_step(*args: object, **kwargs: object) -> DummyCompletion:  # type: ignore[override]
        return DummyCompletion("step")
    monkeypatch.setattr(curriculum_engine, "create_learning_chat_completion", fake_step)
    await curriculum_engine.next_step(1, lesson_id)
    _ = await curriculum_engine.next_step(1, lesson_id)

    async def fake_feedback(*, task: curriculum_engine.LLMTask, messages: list[dict[str, str]], **kwargs: object) -> DummyCompletion:  # type: ignore[override]
        return DummyCompletion("fb")

    monkeypatch.setattr(curriculum_engine, "create_learning_chat_completion", fake_feedback)
    ok, feedback = await curriculum_engine.check_answer(1, lesson_id, 0)
    assert ok is True
    assert feedback == "fb"
    with setup_db() as session:
        prog = session.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == 1,
                LessonProgress.lesson_id == lesson_id,
            )
        ).scalar_one()
        assert prog.quiz_score == 1
        assert prog.completed is True
        assert prog.current_question == 1
