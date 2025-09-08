from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.config import settings
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.curriculum_engine import (
    check_answer,
    next_step,
    start_lesson,
)
from services.api.app.diabetes.dynamic_tutor import BUSY_MESSAGE
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.learning_prompts import disclaimer
from services.api.app.diabetes.models_learning import (
    Lesson,
    LessonProgress,
    LessonStep,
    QuizQuestion,
)
from services.api.app.diabetes.metrics import (
    get_metric_value,
    lessons_completed,
    lessons_started,
    quiz_avg_score,
)
from services.api.app.diabetes.services import db, gpt_client


@pytest.mark.asyncio()
async def test_curriculum_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "static")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    await load_lessons(
        "content/lessons_v0.json",
        sessionmaker=db.SessionLocal,
    )

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        session.commit()
        lesson = session.query(Lesson).first()
        assert lesson is not None
        slug = lesson.slug
        lesson_id = lesson.id

    async def fake_completion(**kwargs: object) -> str:
        fake_completion.calls += 1
        return f"text {fake_completion.calls}"

    fake_completion.calls = 0  # type: ignore[attr-defined]
    monkeypatch.setattr(gpt_client, "create_learning_chat_completion", fake_completion)

    base_started = get_metric_value(lessons_started)
    base_completed = get_metric_value(lessons_completed)
    base_sum = get_metric_value(quiz_avg_score, "sum")
    base_count = get_metric_value(quiz_avg_score, "count")

    progress = await start_lesson(1, slug)
    assert progress.current_step == 0
    assert get_metric_value(lessons_started) == base_started + 1

    first, completed = await next_step(1, lesson_id, {})
    assert completed is False
    assert first == f"{disclaimer()}\n\ntext 1"

    second, completed = await next_step(1, lesson_id, {})
    assert completed is False
    assert second == "text 2"

    third, completed = await next_step(1, lesson_id, {})
    assert completed is False
    assert third == "text 3"

    question_text, completed = await next_step(1, lesson_id, {})
    assert completed is False
    assert question_text.startswith(disclaimer())

    with db.SessionLocal() as session:
        questions = (
            session.query(QuizQuestion)
            .filter_by(lesson_id=lesson_id)
            .order_by(QuizQuestion.id)
            .all()
        )

    first_opts = "\n".join(
        f"{idx}. {opt}" for idx, opt in enumerate(questions[0].options, start=1)
    )
    assert question_text.endswith(first_opts)

    for idx, q in enumerate(questions):
        correct, feedback = await check_answer(1, lesson_id, {}, q.correct_option + 1)
        assert correct is True
        assert feedback
        if idx < len(questions) - 1:
            next_q, completed = await next_step(1, lesson_id, {})
            assert next_q
            assert completed is False

    text, completed = await next_step(1, lesson_id, {})
    assert text is None
    assert completed is True

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        assert progress.completed is True
        assert progress.quiz_score == 100
    assert get_metric_value(lessons_completed) == base_completed + 1
    assert get_metric_value(quiz_avg_score, "sum") == base_sum + 100
    assert get_metric_value(quiz_avg_score, "count") == base_count + 1


@pytest.mark.asyncio()
async def test_lesson_without_quiz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "static")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        lesson = Lesson(title="t", slug="s", content="", is_active=True)
        session.add(lesson)
        session.flush()
        session.add(LessonStep(lesson_id=lesson.id, step_order=1, content="c"))
        session.commit()
        lesson_id = lesson.id

    async def fake_completion(**kwargs: object) -> str:
        return "text"

    monkeypatch.setattr(gpt_client, "create_learning_chat_completion", fake_completion)

    await start_lesson(1, "s")

    first, completed = await next_step(1, lesson_id, {})
    assert first == f"{disclaimer()}\n\ntext"
    assert completed is False

    text, completed = await next_step(1, lesson_id, {})
    assert text is None
    assert completed is True

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        assert progress.completed is True
        assert progress.quiz_score is None


@pytest.mark.asyncio()
async def test_dynamic_mode_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        lesson = Lesson(title="t", slug="s", content="", is_active=True)
        session.add(lesson)
        session.commit()
        lesson_id = lesson.id

    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_generate(
        profile: object, slug: str, step_idx: int, prev: object
    ) -> str:
        fake_generate.calls.append(profile)
        return f"step {step_idx}"

    fake_generate.calls = []  # type: ignore[attr-defined]

    async def fake_check(
        profile: object, slug: str, answer: str, last: str
    ) -> tuple[bool, str]:
        return True, f"fb {answer}"

    monkeypatch.setattr(curriculum_engine, "generate_step_text", fake_generate)
    monkeypatch.setattr(curriculum_engine, "check_user_answer", fake_check)

    profile: dict[str, str] = {"age": "30"}
    await start_lesson(1, "s")
    text, completed = await next_step(1, lesson_id, profile)
    assert text == f"{disclaimer()}\n\nstep 1"
    assert completed is False
    assert fake_generate.calls[0] is profile

    correct, feedback = await check_answer(1, lesson_id, profile, "42")
    assert correct is True
    assert feedback == "fb 42"

    text, completed = await next_step(1, lesson_id, profile)
    assert text == "step 2"
    assert completed is False


@pytest.mark.asyncio()
async def test_check_answer_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    async def fake_run_db(*args: object, **kwargs: object) -> None:
        raise AssertionError("run_db should not be called")

    monkeypatch.setattr(curriculum_engine.db, "run_db", fake_run_db)

    correct, feedback = await check_answer(1, 1, {}, "abc")
    assert (correct, feedback) == (
        False,
        "Пожалуйста, выберите номер варианта",
    )


@pytest.mark.asyncio()
async def test_next_step_handles_gpt_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "static")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        lesson = Lesson(title="t", slug="s", content="", is_active=True)
        session.add(lesson)
        session.flush()
        session.add(LessonStep(lesson_id=lesson.id, step_order=1, content="c"))
        session.commit()
        lesson_id = lesson.id

    await start_lesson(1, "s")

    async def fail_completion(**kwargs: object) -> str:  # pragma: no cover - test
        raise RuntimeError("boom")

    monkeypatch.setattr(
        gpt_client,
        "create_learning_chat_completion",
        fail_completion,
    )

    text, completed = await next_step(1, lesson_id, {})
    assert text == BUSY_MESSAGE
    assert completed is False


@pytest.mark.asyncio()
async def test_next_step_dynamic_busy_does_not_increment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        lesson = Lesson(title="t", slug="s", content="", is_active=True)
        session.add(lesson)
        session.commit()
        lesson_id = lesson.id

    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_generate(
        profile: object, slug: str, step_idx: int, prev: object
    ) -> str:
        return BUSY_MESSAGE

    monkeypatch.setattr(curriculum_engine, "generate_step_text", fake_generate)

    await start_lesson(1, "s")
    text, completed = await next_step(1, lesson_id, {})
    assert text == BUSY_MESSAGE
    assert completed is False

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        assert progress.current_step == 0


@pytest.mark.asyncio()
async def test_next_step_dynamic_exception_does_not_increment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        lesson = Lesson(title="t", slug="s", content="", is_active=True)
        session.add(lesson)
        session.commit()
        lesson_id = lesson.id

    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fail_generate(
        profile: object, slug: str, step_idx: int, prev: object
    ) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(curriculum_engine, "generate_step_text", fail_generate)

    await start_lesson(1, "s")
    text, completed = await next_step(1, lesson_id, {})
    assert text == BUSY_MESSAGE
    assert completed is False

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        assert progress.current_step == 0
