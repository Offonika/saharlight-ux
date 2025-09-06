from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes.handlers import learning_handlers
from services.api.app.diabetes.learning_state import get_state


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.replies: list[str] = []
        self.text = text

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)


def make_update(text: str = "") -> Update:
    user = SimpleNamespace(id=1)
    return cast(
        Update, SimpleNamespace(message=DummyMessage(text), effective_user=user)
    )


def make_context(**kwargs: Any) -> CallbackContext[Any, Any, Any, Any]:
    data: dict[str, Any] = {"user_data": {}, "args": []}
    data.update(kwargs)
    return cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace(**data))


@pytest.mark.asyncio
async def test_text_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    questions = iter([("Q1", False), (None, True)])

    async def fake_next(user_id: int, lesson_id: int) -> tuple[str | None, bool]:
        return next(questions)

    async def fake_check(user_id: int, lesson_id: int, answer: int) -> tuple[bool, str]:
        return True, "ok"

    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "check_answer", fake_check)

    user_data = {"lesson_id": 1}

    upd1 = make_update()
    ctx1 = make_context(user_data=user_data, args=[])
    await learning_handlers.quiz_command(upd1, ctx1)
    msg1 = cast(DummyMessage, upd1.message)
    assert msg1.replies == ["Q1"]

    upd2 = make_update("1")
    ctx2 = make_context(user_data=user_data)
    await learning_handlers.quiz_answer_handler(upd2, ctx2)
    msg2 = cast(DummyMessage, upd2.message)
    assert msg2.replies == ["ok", "Опрос завершён"]
    assert get_state(user_data) is None
