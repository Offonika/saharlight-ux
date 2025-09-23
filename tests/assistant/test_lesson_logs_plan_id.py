from __future__ import annotations
from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.models import LessonLog
from services.api.app.assistant.repositories import logs
from services.api.app.assistant.repositories import learning_profile as learning_profile_repo
from services.api.app.assistant.repositories import plans as plans_repo
from services.api.app.assistant.services import progress_service as progress_repo
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.models_learning import LearningPlan
from services.api.app.diabetes.services import db
from services.api.app.diabetes.services.db import User


class _DummyMessage:
    def __init__(self, text: str = "", user_id: int = 1) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self._replies: list[str] = []

    @property
    def replies(self) -> list[str]:
        return self._replies

    async def reply_text(self, text: str, **_kwargs: Any) -> SimpleNamespace:
        self._replies.append(text)
        return SimpleNamespace(message_id=len(self._replies))


@pytest.mark.asyncio()
async def test_logs_are_stored_with_plan_id(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lesson logs should persist using the actual plan identifier."""

    logs.pending_logs.clear()

    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="thread"))
        session.commit()

    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)
    monkeypatch.setattr(learning_handlers.settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")

    async def fake_ensure_overrides(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(
        learning_handlers,
        "choose_initial_topic",
        lambda _profile: ("intro", "Intro"),
    )

    steps = iter([
        ("Первый шаг", False),
        ("Второй шаг", False),
    ])

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=42)

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Any,
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        try:
            return next(steps)
        except StopIteration:
            return "", True

    monkeypatch.setattr(
        learning_handlers.curriculum_engine,
        "start_lesson",
        fake_start_lesson,
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine,
        "next_step",
        fake_next_step,
    )

    async def fake_assistant_chat(_profile: Any, _text: str) -> str:
        return "Подсказка"

    monkeypatch.setattr(learning_handlers, "assistant_chat", fake_assistant_chat)

    context = SimpleNamespace(user_data={}, bot_data={}, args=[])

    learn_message = _DummyMessage(text="/learn")
    learn_update = SimpleNamespace(
        message=learn_message,
        effective_user=learn_message.from_user,
    )

    await learning_handlers.learn_command(learn_update, context)

    plan_id = context.user_data.get("learning_plan_id")
    assert isinstance(plan_id, int)

    with session_factory() as session:
        plan_rows = session.query(LearningPlan).all()
        assert {p.id for p in plan_rows} == {plan_id}

    answer_message = _DummyMessage(text="Не знаю")
    answer_update = SimpleNamespace(
        message=answer_message,
        effective_user=answer_message.from_user,
    )

    await learning_handlers.lesson_answer_handler(answer_update, context)

    with session_factory() as session:
        rows = session.query(LessonLog).order_by(LessonLog.id).all()

    assert len(rows) >= 3
    assert {row.plan_id for row in rows} == {plan_id}
    assert not logs.pending_logs
    unique_steps = {
        (row.module_idx, row.step_idx, row.role)
        for row in rows
    }
    assert len(unique_steps) == len(rows)

    logs.pending_logs.clear()


@pytest.mark.asyncio()
async def test_safe_add_lesson_log_handles_duplicates(
    session_factory: sessionmaker[Session],
) -> None:
    """Sequential duplicate calls should be idempotent for a plan."""

    logs.pending_logs.clear()

    with session_factory() as session:
        user = User(telegram_id=1, thread_id="thread")
        session.add(user)
        plan = LearningPlan(user_id=1, plan_json=["step"])
        session.add(plan)
        session.commit()
        plan_id = plan.id

    assert await logs.safe_add_lesson_log(1, plan_id, 0, 0, "assistant", "hello") is True
    assert await logs.safe_add_lesson_log(1, plan_id, 0, 0, "assistant", "hello") is True
    assert await logs.safe_add_lesson_log(1, plan_id, 0, 1, "user", "hi") is True

    with session_factory() as session:
        rows = (
            session.query(LessonLog)
            .filter(LessonLog.plan_id == plan_id)
            .order_by(LessonLog.id)
            .all()
        )

    assert {(row.module_idx, row.step_idx, row.role) for row in rows} == {
        (0, 0, "assistant"),
        (0, 1, "user"),
    }
    assert len(rows) == 2
    assert not logs.pending_logs

    logs.pending_logs.clear()


@pytest.fixture()
def session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(learning_handlers, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(plans_repo, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(progress_repo, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(learning_profile_repo, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(logs, "SessionLocal", session_local, raising=False)
    try:
        yield session_local
    finally:
        db.dispose_engine(engine)
