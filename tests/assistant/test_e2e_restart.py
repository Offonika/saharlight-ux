from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import plans as plans_repo
from services.api.app.assistant.services import progress_service as progress_repo
from services.api.app.diabetes.services import db
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.planner import generate_learning_plan, pretty_plan
from services.api.app.diabetes.models_learning import LearningProgress


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
async def test_restart_restores_step(
    monkeypatch: pytest.MonkeyPatch, setup_db: sessionmaker[Session]
) -> None:
    """Ensure progress survives service restart and plan continues from step 2."""

    with setup_db() as session:  # type: ignore[misc]
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()
    plan_id = await plans_repo.create_plan(1, version=1, plan_json=["Шаг 1", "Шаг 2"])
    await progress_repo.upsert_progress(
        1,
        plan_id,
        {"topic": "intro", "module_idx": 0, "step_idx": 2, "snapshot": "Шаг 2"},
    )

    update = SimpleNamespace(
        message=DummyMessage(), effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={}, bot_data={})
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)
    monkeypatch.setattr(learning_handlers.settings, "learning_content_mode", "dynamic")

    await learning_handlers.plan_command(update, context)
    state = learning_handlers.get_state(context.user_data)
    assert state is not None
    assert state.step == 2
    assert context.user_data.get("learning_plan_index") == 1
    assert update.message.sent
    assert "Шаг 2" in update.message.sent[0]


@pytest.mark.asyncio
async def test_hydrate_generates_snapshot_and_persists(
    monkeypatch: pytest.MonkeyPatch, setup_db: sessionmaker[Session]
) -> None:
    """Full flow: learn → 'Не знаю' → restart → plan and learn continue."""

    with setup_db() as session:  # type: ignore[misc]
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()

    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)
    monkeypatch.setattr(learning_handlers.settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")
    async def fake_profile(*_: object) -> dict[str, str | None]:
        return {}

    monkeypatch.setattr(
        learning_handlers.profiles, "get_profile_for_user", fake_profile
    )

    async def fake_ensure_overrides(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(
        learning_handlers, "choose_initial_topic", lambda _p: ("intro", "Intro")
    )

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    gen_calls: list[int] = []

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Any,
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        step_idx = len(gen_calls) + 1
        gen_calls.append(step_idx)
        return f"Шаг {step_idx}", False

    async def fake_generate_step_text(
        _profile: Any, _topic: str, step_idx: int, _prev: str | None
    ) -> str:
        gen_calls.append(step_idx)
        return f"Шаг {step_idx}"

    async def fake_assistant_chat(_profile: Any, _text: str) -> str:
        return "feedback"

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )
    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)
    monkeypatch.setattr(learning_handlers, "assistant_chat", fake_assistant_chat)

    async def fake_add_log(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

    calls: list[dict[str, Any]] = []
    orig_upsert = progress_repo.upsert_progress

    async def spy_upsert(
        user_id: int, plan_id: int, progress_json: dict[str, Any]
    ) -> Any:
        calls.append(progress_json.copy())
        return await orig_upsert(user_id, plan_id, progress_json)

    monkeypatch.setattr(progress_repo, "upsert_progress", spy_upsert)

    msg_learn = DummyMessage(text="/learn")
    update = SimpleNamespace(message=msg_learn, effective_user=msg_learn.from_user)
    context = SimpleNamespace(user_data={}, bot_data={})
    await learning_handlers.learn_command(update, context)
    plan = generate_learning_plan("Шаг 1")
    assert msg_learn.sent == [f"\U0001F5FA План обучения\n{pretty_plan(plan)}", "Шаг 1"]
    assert len(calls) == 1

    msg_ans = DummyMessage(text="Не знаю")
    upd_ans = SimpleNamespace(message=msg_ans, effective_user=msg_ans.from_user)
    await learning_handlers.lesson_answer_handler(upd_ans, context)
    assert msg_ans.sent == ["feedback", "Шаг 2"]
    assert len(calls) == 2

    with setup_db() as session:  # type: ignore[misc]
        progress = session.query(LearningProgress).one()
        progress.progress_json = {**progress.progress_json, "snapshot": None}
        session.add(progress)
        session.commit()

    context2 = SimpleNamespace(user_data={}, bot_data={})
    plan_msg = DummyMessage()
    upd_plan = SimpleNamespace(message=plan_msg, effective_user=plan_msg.from_user)
    await learning_handlers.plan_command(upd_plan, context2)

    assert context2.user_data.get("learning_plan_index") == 1
    assert len(calls) == 3
    assert gen_calls == [1, 2, 2]

    msg_learn2 = DummyMessage(text="/learn")
    upd_learn2 = SimpleNamespace(
        message=msg_learn2, effective_user=msg_learn2.from_user
    )
    await learning_handlers.learn_command(upd_learn2, context2)
    assert msg_learn2.sent == ["Шаг 2"]
