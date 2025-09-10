from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Mapping, Type

import httpx
import pytest
from openai import OpenAIError
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers as dynamic_handlers
from services.api.app.diabetes.dynamic_tutor import BUSY_MESSAGE
from services.api.app.diabetes.learning_state import get_state
from tests.utils.telegram import make_context, make_update


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []
        self.markups: list[Any] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)
        self.markups.append(kwargs.get("reply_markup"))


EXCEPTIONS: tuple[Type[Exception], ...] = (
    SQLAlchemyError,
    OpenAIError,
    httpx.HTTPError,
    RuntimeError,
)


async def _ok_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
    return SimpleNamespace(lesson_id=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", EXCEPTIONS)
async def test_learn_command_start_lesson_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exc: Type[Exception],
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(
        dynamic_handlers, "choose_initial_topic", lambda _p: ("slug", "t")
    )
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)

    async def fail_next_step(*args: object, **kwargs: object) -> tuple[str, bool]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "next_step", fail_next_step)

    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise exc("boom")  # type: ignore[arg-type]

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson
    )

    def fail_generate_learning_plan(_text: str) -> list[str]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(
        dynamic_handlers, "generate_learning_plan", fail_generate_learning_plan
    )

    async def fail_add_log(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "safe_add_lesson_log", fail_add_log)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    with caplog.at_level(logging.ERROR):
        await dynamic_handlers.learn_command(update, context)

    assert msg.replies == [BUSY_MESSAGE]
    assert get_state(context.user_data) is None
    assert any("lesson start failed" in r.message for r in caplog.records)
    assert context.user_data.get("lesson_id") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", EXCEPTIONS)
async def test_learn_command_next_step_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exc: Type[Exception],
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(
        dynamic_handlers, "choose_initial_topic", lambda _p: ("slug", "t")
    )
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", _ok_start_lesson
    )

    async def raise_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        raise exc("boom")  # type: ignore[arg-type]

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "next_step", raise_next_step
    )

    def fail_generate_learning_plan(_text: str) -> list[str]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(
        dynamic_handlers, "generate_learning_plan", fail_generate_learning_plan
    )

    async def fail_add_log(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "safe_add_lesson_log", fail_add_log)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    with caplog.at_level(logging.ERROR):
        await dynamic_handlers.learn_command(update, context)

    assert msg.replies == [BUSY_MESSAGE]
    assert get_state(context.user_data) is None
    assert any("lesson start failed" in r.message for r in caplog.records)
    assert context.user_data.get("lesson_id") is None


@pytest.mark.asyncio
async def test_lesson_command_start_lesson_exception(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(dynamic_handlers, "TOPICS_RU", {"slug": "Topic"})
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(dynamic_handlers, "disclaimer", lambda: "")

    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson
    )

    async def fail_next_step(*args: object, **kwargs: object) -> tuple[str, bool]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "next_step", fail_next_step)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    with caplog.at_level(logging.ERROR):
        await dynamic_handlers.lesson_command(update, context)

    assert msg.replies == [BUSY_MESSAGE]
    assert get_state(context.user_data) is None
    assert any("lesson start failed" in r.message for r in caplog.records)
    assert context.user_data.get("lesson_id") is None


@pytest.mark.asyncio
async def test_lesson_command_next_step_exception(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(dynamic_handlers, "TOPICS_RU", {"slug": "Topic"})
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(dynamic_handlers, "disclaimer", lambda: "")

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", _ok_start_lesson
    )

    async def raise_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "next_step", raise_next_step
    )

    def fail_generate_learning_plan(_text: str) -> list[str]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(
        dynamic_handlers, "generate_learning_plan", fail_generate_learning_plan
    )

    async def fail_add_log(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "safe_add_lesson_log", fail_add_log)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    with caplog.at_level(logging.ERROR):
        await dynamic_handlers.lesson_command(update, context)

    assert msg.replies == [BUSY_MESSAGE]
    assert get_state(context.user_data) is None
    assert any("lesson start failed" in r.message for r in caplog.records)
    assert context.user_data.get("lesson_id") is None
