from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import plans as plans_repo
from services.api.app.assistant.services import progress_service as progress_repo
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.services import db


class DummyMessage:
    """Capture replies and emulate minimal Telegram Message."""

    def __init__(self, text: str = "", user_id: int = 1) -> None:
        self.sent: list[str] = []
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)

    async def reply_text(self, text: str, **_kwargs: Any) -> None:
        self.sent.append(text)


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
async def test_plan_button_flow(
    monkeypatch: pytest.MonkeyPatch, setup_db: sessionmaker[Session]
) -> None:
    """Full flow: /learn → step1 → 'Не знаю' → feedback+step2 → /plan."""

    with setup_db() as session:  # type: ignore[misc]
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()

    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)
    monkeypatch.setattr(learning_handlers.settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")

    async def fake_ensure_overrides(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(
        learning_handlers, "choose_initial_topic", lambda _p: ("intro", "Intro")
    )

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    step = 0

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Any,
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        nonlocal step
        step += 1
        return f"Шаг {step}", False

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )

    async def fake_assistant_chat(_profile: Any, _text: str) -> str:
        return "feedback"

    monkeypatch.setattr(learning_handlers, "assistant_chat", fake_assistant_chat)

    async def fake_add_log(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

    msg_learn = DummyMessage(text="/learn")
    update_learn = SimpleNamespace(
        message=msg_learn, effective_user=msg_learn.from_user
    )
    context = SimpleNamespace(user_data={}, bot_data={})
    await learning_handlers.learn_command(update_learn, context)
    assert msg_learn.sent == ["Шаг 1"]

    msg_ans = DummyMessage(text="Не знаю")
    update_ans = SimpleNamespace(
        message=msg_ans, effective_user=msg_ans.from_user
    )
    await learning_handlers.lesson_answer_handler(update_ans, context)
    assert msg_ans.sent == ["feedback", "Шаг 2"]

    plan_msg = DummyMessage()
    plan_update = SimpleNamespace(
        message=plan_msg, effective_user=plan_msg.from_user
    )
    await learning_handlers.plan_command(plan_update, context)
    assert plan_msg.sent
    assert "Шаг 2" in plan_msg.sent[0]
