from types import SimpleNamespace
from typing import Any, Mapping, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.planner import generate_learning_plan, pretty_plan


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: object) -> None:
        self.replies.append(text)


def test_generate_and_pretty_plan() -> None:
    plan = generate_learning_plan("step1")
    assert plan[0] == "step1"
    assert pretty_plan(plan[:2]) == "1. step1\n2. Шаг 2: контроль питания"


@pytest.mark.asyncio
async def test_learn_command_stores_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    async def fake_ensure_overrides(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return "step1", False

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )
    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await learning_handlers.learn_command(update, context)

    assert context.user_data["learning_plan_index"] == 0
    assert context.user_data["learning_plan"][0] == "step1"
    assert message.replies == ["step1"]


@pytest.mark.asyncio
async def test_plan_and_skip_commands() -> None:
    plan = ["step1", "step2"]
    user_data = {"learning_plan": plan, "learning_plan_index": 0}
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    await learning_handlers.plan_command(update, context)
    assert message.replies[-1] == pretty_plan(plan)

    await learning_handlers.skip_command(update, context)
    assert message.replies[-1] == "step2"
    assert user_data["learning_plan_index"] == 1

    await learning_handlers.skip_command(update, context)
    assert message.replies[-1] == "План завершён."
    assert user_data["learning_plan_index"] == 2
