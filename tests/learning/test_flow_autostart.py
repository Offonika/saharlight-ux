from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from types import SimpleNamespace

import pytest
from telegram import Bot, Chat, Message, MessageEntity, Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from services.api.app.config import TOPICS_RU, settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.handlers import learning_onboarding
from services.api.app.diabetes.planner import generate_learning_plan, pretty_plan


class DummyBot(Bot):
    """Lightweight bot recording sent messages for assertions."""

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
    def username(self) -> str:  # pragma: no cover - simple proxy
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


@pytest.mark.asyncio()
async def test_flow_autostart(monkeypatch: pytest.MonkeyPatch) -> None:
    """Autostart should skip topic list and send first dynamic step."""

    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    title = next(iter(TOPICS_RU.values()))

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    captured_profile: Mapping[str, str | None] = {}

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        nonlocal captured_profile
        captured_profile = profile
        return "шаг1", False

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )
    monkeypatch.setattr(
        learning_handlers.lesson_log, "safe_add_lesson_log", fake_add_log
    )

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, learning_onboarding.onboarding_reply
        )
    )
    await app.initialize()

    user = User(id=1, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")

    def _msg(
        mid: int, text: str, *, entities: list[MessageEntity] | None = None
    ) -> Message:
        msg = Message(
            message_id=mid,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            text=text,
            entities=entities,
        )
        msg._bot = bot
        return msg

    # start onboarding
    await app.process_update(
        Update(
            update_id=1,
            message=_msg(1, "/learn", entities=[MessageEntity("bot_command", 0, 6)]),
        )
    )
    await app.process_update(Update(update_id=2, message=_msg(2, "49")))
    await app.process_update(Update(update_id=3, message=_msg(3, "0")))
    expected_plan = generate_learning_plan("шаг1")
    assert bot.sent[-2] == f"\U0001f5fa План обучения\n{pretty_plan(expected_plan)}"
    assert bot.sent[-1] == "шаг1"
    assert all(
        title not in s and "Выберите тему" not in s and "Доступные темы" not in s
        for s in bot.sent
    )
    assert captured_profile == {
        "age_group": "adult",
        "learning_level": "novice",
    }

    await app.shutdown()
