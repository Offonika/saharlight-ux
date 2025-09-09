from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from telegram import Bot, Chat, Message, MessageEntity, Update, User
from telegram.ext import Application, CommandHandler

from services.api.app.config import settings
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes import learning_handlers as dynamic_handlers
from services.api.app.diabetes.handlers import learning_handlers


class DummyBot(Bot):
    """Minimal bot capturing sent messages for assertions."""

    def __init__(self) -> None:
        super().__init__(token="123:ABC")
        object.__setattr__(self, "_sent", [])

    @property
    def sent(self) -> list[str]:  # pragma: no cover - simple proxy
        return self._sent  # type: ignore[attr-defined]

    async def initialize(self) -> None:  # pragma: no cover - setup
        self._me = User(id=0, is_bot=True, first_name="Bot", username="bot")
        self._bot = self
        self._initialized = True

    @property
    def username(self) -> str:  # pragma: no cover - simple property
        return "bot"

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> Message:
        msg = Message(
            message_id=len(self.sent) + 1,
            date=datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            from_user=self._me,
            text=text,
        )
        msg._bot = self
        self.sent.append(text)
        return msg


async def _fake_persist(*args: object, **kwargs: object) -> None:
    return None


@pytest.mark.asyncio
async def test_dynamic_mode_empty_lessons(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dynamic /learn should not depend on lessons table."""

    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", False)

    async def fake_generate_step_text(*_a: object, **_k: object) -> str:
        return "step1"

    monkeypatch.setattr(dynamic_handlers, "generate_step_text", fake_generate_step_text)

    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise curriculum_engine.LessonNotFoundError(slug)

    async def fail_next_step(*args: object, **kwargs: object) -> tuple[str, bool]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson
    )
    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "next_step", fail_next_step
    )
    monkeypatch.setattr(
        dynamic_handlers,
        "generate_learning_plan",
        lambda *_a, **_k: ["step1", "step2"],
    )
    monkeypatch.setattr(dynamic_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(dynamic_handlers, "disclaimer", lambda: "")
    monkeypatch.setattr(dynamic_handlers, "add_lesson_log", _fake_persist)
    monkeypatch.setattr(dynamic_handlers.plans_repo, "get_active_plan", _fake_persist)
    monkeypatch.setattr(dynamic_handlers.plans_repo, "create_plan", _fake_persist)
    monkeypatch.setattr(dynamic_handlers.plans_repo, "update_plan", _fake_persist)
    monkeypatch.setattr(dynamic_handlers.progress_service, "upsert_progress", _fake_persist)

    async def fake_ensure_overrides(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(dynamic_handlers, "choose_initial_topic", lambda _p: ("slug", "t"))

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    await app.initialize()

    user = User(id=1, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")
    msg = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="/learn",
        entities=[MessageEntity(type="bot_command", offset=0, length=6)],
    )
    msg._bot = bot
    await app.process_update(Update(update_id=1, message=msg))

    assert bot.sent == [
        "\U0001F5FA План обучения\n1. step1\n2. step2",
        "step1",
    ]

    await app.shutdown()


@pytest.mark.asyncio
async def test_static_mode_empty_lessons_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Static /learn should fall back to dynamic when no lessons."""

    monkeypatch.setattr(settings, "learning_content_mode", "static")
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    async def fake_run_db(*_a: object, **_k: object) -> list[tuple[str, str]]:
        return []

    monkeypatch.setattr(learning_handlers, "run_db", fake_run_db)

    async def fake_ensure_overrides(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    called: list[str] = []

    async def fake_learn(update: Update, context: Any) -> None:
        assert update.message is not None
        await update.message.reply_text("dynamic step")
        called.append("ok")

    monkeypatch.setattr(dynamic_handlers, "learn_command", fake_learn)

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    await app.initialize()

    user = User(id=1, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")
    msg = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="/learn",
        entities=[MessageEntity(type="bot_command", offset=0, length=6)],
    )
    msg._bot = bot
    await app.process_update(Update(update_id=1, message=msg))

    assert bot.sent == ["dynamic step"]
    assert called == ["ok"]

    await app.shutdown()
