from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_timezone_save_creates_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_db(func, sessionmaker):
        if func.__name__ == "db_set_timezone":
            return False, True
        if func.__name__ == "db_get_reminders":
            return []
        raise AssertionError(func)

    monkeypatch.setattr(handlers, "run_db", run_db)

    msg = DummyMessage("Europe/Moscow")
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(job_queue=SimpleNamespace()),
    )

    await handlers.profile_timezone_save(update, context)
    assert msg.replies == ["✅ Профиль создан. Часовой пояс сохранён."]
