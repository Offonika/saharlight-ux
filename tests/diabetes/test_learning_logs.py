from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import logging
import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes.handlers import learning_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: object) -> None:
        self.replies.append(text)


def make_update() -> Update:
    user = SimpleNamespace(id=1)
    return cast(Update, SimpleNamespace(message=DummyMessage(), effective_user=user))


def make_context(**kwargs: Any) -> CallbackContext[Any, Any, Any, Any]:
    data: dict[str, Any] = {"user_data": {}, "args": []}
    data.update(kwargs)
    return cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace(**data))


@pytest.mark.asyncio
async def test_lesson_start_logging(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Ensure starting a lesson logs start and completion events."""
    monkeypatch.setattr(settings, "learning_enabled", True)

    async def fake_start(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    async def fake_next(user_id: int, lesson_id: int) -> str | None:
        return None

    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next)

    upd = make_update()
    ctx = make_context(args=["l1"])

    with caplog.at_level(logging.INFO):
        await learning_handlers.lesson_command(upd, ctx)

    assert any(r.message == "lesson_command_start" for r in caplog.records)
    assert any(r.message == "lesson_command_complete" for r in caplog.records)


@pytest.mark.asyncio
async def test_exit_logging(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Ensure exiting a lesson logs start and completion events."""
    monkeypatch.setattr(settings, "learning_enabled", True)
    async def fake_run_db(*args: Any, **kwargs: Any) -> None:  # pragma: no cover - simple stub
        return None

    monkeypatch.setattr(learning_handlers, "run_db", fake_run_db)
    upd = make_update()
    ctx = make_context(user_data={"lesson_id": 1})

    with caplog.at_level(logging.INFO):
        await learning_handlers.exit_command(upd, ctx)

    assert any(r.message == "exit_command_start" for r in caplog.records)
    assert any(r.message == "exit_command_complete" for r in caplog.records)
