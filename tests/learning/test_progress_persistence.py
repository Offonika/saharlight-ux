from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState, set_state
from services.api.app.diabetes.models_learning import ProgressData


@pytest.mark.asyncio
async def test_persist_saves_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    user_data: dict[str, Any] = {
        "learning_plan": ["a"],
        "learning_plan_id": 1,
        "learning_module_idx": 3,
    }
    state = LearnState(topic="intro", step=2, last_step_text="s", prev_summary="p")
    set_state(user_data, state)
    bot_data: dict[str, object] = {}

    calls: list[tuple[int, int, ProgressData]] = []

    async def fake_update_plan(plan_id: int, plan_json: list[str]) -> None:
        return None

    async def fake_upsert(uid: int, pid: int, data: ProgressData) -> None:
        calls.append((uid, pid, data))

    monkeypatch.setattr(learning_handlers.plans_repo, "update_plan", fake_update_plan)
    monkeypatch.setattr(learning_handlers.progress_repo, "upsert_progress", fake_upsert)

    await learning_handlers._persist(1, user_data, bot_data)

    expected: ProgressData = {
        "topic": "intro",
        "module_idx": 3,
        "step_idx": 2,
        "snapshot": "s",
        "prev_summary": "p",
    }
    progress_map = bot_data[learning_handlers.PROGRESS_KEY]
    assert progress_map == {1: expected}
    assert calls == [(1, 1, expected)]


@pytest.mark.asyncio
async def test_hydrate_loads_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = ["a", "b"]
    progress: ProgressData = {
        "topic": "intro",
        "module_idx": 1,
        "step_idx": 1,
        "snapshot": "snap",
        "prev_summary": None,
    }

    async def fake_get_active_plan(user_id: int) -> Any:
        return SimpleNamespace(id=1, plan_json=plan)

    async def fake_get_progress(user_id: int, plan_id: int) -> Any:
        return SimpleNamespace(progress_json=progress)

    async def fake_get_profile(user_id: int) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.plans_repo, "get_active_plan", fake_get_active_plan
    )
    monkeypatch.setattr(
        learning_handlers.progress_repo, "get_progress", fake_get_progress
    )
    monkeypatch.setattr(learning_handlers, "get_learning_profile", fake_get_profile)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1), effective_message=None
    )
    context = SimpleNamespace(user_data={}, bot_data={})

    ok = await learning_handlers._hydrate(update, context)
    assert ok is True

    state = learning_handlers.get_state(context.user_data)
    assert state is not None
    assert state.topic == "intro"
    assert state.step == 1
    assert state.last_step_text == "snap"
    assert context.user_data["learning_plan"] == plan
    assert context.user_data["learning_plan_index"] == 0
    assert context.user_data["learning_plan_id"] == 1
