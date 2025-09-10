from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app import profiles
from services.api.app.assistant.repositories import plans as plans_repo
from services.api.app.assistant.services import progress_service as progress_repo
from services.api.app.diabetes import learning_handlers, learning_onboarding
from services.api.app.diabetes.handlers import (
    learning_onboarding as onboarding_handlers,
)
from services.api.app.diabetes.services import db


class DummyMessage:
    """Minimal Telegram message capturing replies."""

    def __init__(self, text: str = "", user_id: int = 1) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.sent: list[str] = []

    async def reply_text(self, text: str, **_kwargs: Any) -> None:
        self.sent.append(text)

    async def reply_video(self, video: Any, **_kwargs: Any) -> None:
        self.sent.append(video)


@pytest.fixture()
def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(plans_repo, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(progress_repo, "SessionLocal", session_local, raising=False)
    yield session_local
    db.dispose_engine(engine)


@pytest.mark.asyncio
@pytest.mark.parametrize("question", ["T1", "T2"])
async def test_first_run_restart_and_type_questions(
    monkeypatch: pytest.MonkeyPatch, setup_db: sessionmaker[Session], question: str
) -> None:
    with setup_db() as session:  # type: ignore[misc]
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()

    profile_store = {"diabetes_type": "T1"}

    async def fake_get_profile(user_id: int, ctx: Any) -> dict[str, Any]:
        return profile_store

    monkeypatch.setattr(profiles, "get_profile_for_user", fake_get_profile)
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)
    monkeypatch.setattr(learning_handlers.settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")
    monkeypatch.setattr(learning_handlers, "choose_initial_topic", lambda _p: ("intro", "Intro"))

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    steps = iter(["Шаг 1", "Шаг 2"])

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Any,
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return next(steps), False

    async def fake_assistant_chat(_profile: Any, _text: str) -> str:
        return "feedback"

    async def fake_check_user_answer(
        _profile: Any, _topic: str, _text: str, _prev: str
    ) -> tuple[bool, str]:
        return False, "feedback"

    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next_step)
    monkeypatch.setattr(learning_handlers, "assistant_chat", fake_assistant_chat)
    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(
        learning_handlers, "generate_learning_plan", lambda first_step=None: [first_step or "Шаг 1", "Шаг 2"]
    )
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)
    async def fake_add_log(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    msg = DummyMessage(text="/learn")
    update = SimpleNamespace(message=msg, effective_user=msg.from_user)
    context = SimpleNamespace(user_data={}, bot_data={})
    await learning_handlers.learn_command(update, context)
    assert msg.sent == [learning_onboarding.AGE_PROMPT]

    msg_age = DummyMessage(text="49")
    upd_age = SimpleNamespace(message=msg_age, effective_user=msg_age.from_user)
    await onboarding_handlers.onboarding_reply(upd_age, context)
    assert msg_age.sent == [learning_onboarding.LEARNING_LEVEL_PROMPT]

    msg_level = DummyMessage(text="0")
    upd_level = SimpleNamespace(message=msg_level, effective_user=msg_level.from_user)
    await onboarding_handlers.onboarding_reply(upd_level, context)
    from services.api.app.diabetes.planner import pretty_plan

    plan = ["Шаг 1", "Шаг 2"]
    assert msg_level.sent == [f"\U0001F5FA План обучения\n{pretty_plan(plan)}", "Шаг 1"]

    msg_q = DummyMessage(text=question)
    upd_q = SimpleNamespace(message=msg_q, effective_user=msg_q.from_user)
    await learning_handlers.lesson_answer_handler(upd_q, context)
    assert msg_q.sent == ["feedback", "Шаг 2"]

    profile_store.update(context.user_data.get("learn_profile_overrides", {}))

    context2 = SimpleNamespace(user_data={}, bot_data={})
    msg2 = DummyMessage(text="/learn")
    upd2 = SimpleNamespace(message=msg2, effective_user=msg2.from_user)
    await learning_handlers.learn_command(upd2, context2)
    assert msg2.sent == ["Шаг 2"]
