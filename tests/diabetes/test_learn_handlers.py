from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "learn_handlers",
    Path(__file__).resolve().parents[2]
    / "services/api/app/diabetes/handlers/learn_handlers.py",
)
assert spec and spec.loader
learn_handlers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learn_handlers)  # type: ignore[misc]


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_learn_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learn_handlers.learn_command(update, context)
    assert message.replies == ["режим выключен"]


@pytest.mark.asyncio
async def test_learn_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_model_default", "super-model")
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learn_handlers.learn_command(update, context)
    assert "super-model" in message.replies[0]
