from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from telegram import Update
from telegram.ext import CallbackContext

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_profile_timezone_save_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(handlers, "build_timezone_webapp_button", lambda: None)
    run_db = AsyncMock()
    monkeypatch.setattr(handlers, "run_db", run_db)
    message = DummyMessage("Bad/Zone")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.PROFILE_TZ
    assert any("Некорректный часовой пояс" in r for r in message.replies)
    assert run_db.await_count == 0


@pytest.mark.asyncio
async def test_profile_timezone_save_db_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_db = AsyncMock(return_value=(True, False))
    monkeypatch.setattr(handlers, "run_db", run_db)
    message = DummyMessage("Europe/Moscow")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.END
    assert any("Не удалось обновить" in r for r in message.replies)
    run_db.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_timezone_save_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reminder_user = SimpleNamespace(id=1)
    reminder = SimpleNamespace(id=5, user=reminder_user)

    async def run_db(fn, *, sessionmaker) -> Any:
        run_db.calls += 1
        if run_db.calls == 1:
            return True, True
        return [reminder]

    run_db.calls = 0
    monkeypatch.setattr(handlers, "run_db", run_db)

    calls: list[tuple[Any, Any, Any]] = []

    def reschedule(job_queue: Any, rem: Any, user: Any) -> None:
        calls.append((job_queue, rem, user))

    monkeypatch.setattr(handlers.reminder_handlers, "_reschedule_job", reschedule)

    job_queue = object()
    message = DummyMessage("Europe/Moscow")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(job_queue=job_queue),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.END
    assert any("Часовой пояс обновлён" in r for r in message.replies)
    assert calls == [(job_queue, reminder, reminder_user)]
    assert run_db.calls == 2
