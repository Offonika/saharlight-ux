from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from telegram import Bot, Chat, Message, MessageEntity, Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.handlers import learning_onboarding


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

    async def fake_generate_step_text(*args: object, **kwargs: object) -> str:
        return "шаг1"

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)
    monkeypatch.setattr(
        learning_handlers, "choose_initial_topic", lambda _: ("slug", "Topic")
    )
    progress = SimpleNamespace(lesson_id=1)

    async def fake_start_lesson(user_id: int, slug: str) -> object:
        assert slug == "slug"
        return progress

    async def fake_next_step(user_id: int, lesson_id: int) -> tuple[str, bool]:
        assert lesson_id == progress.lesson_id
        return "шаг1", False

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
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
    await app.process_update(Update(update_id=3, message=_msg(3, "2")))
    await app.process_update(Update(update_id=4, message=_msg(4, "0")))

    # call /learn again - should autostart first topic
    await app.process_update(
        Update(
            update_id=5,
            message=_msg(5, "/learn", entities=[MessageEntity("bot_command", 0, 6)]),
        )
    )

    assert bot.sent[-1:] == ["шаг1"]
    assert all("Выберите тему" not in s and "Доступные темы" not in s for s in bot.sent)

    await app.shutdown()
