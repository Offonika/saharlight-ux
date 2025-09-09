from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import pytest
from telegram import Bot, Chat, Message, MessageEntity, Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.handlers import learning_onboarding


class DummyBot(Bot):
    """Bot that stores sent messages for assertions."""

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


async def _noop(*args: object, **kwargs: object) -> None:
    return None


@pytest.mark.asyncio
async def test_onboarding_completion_triggers_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", False)

    async def fake_get_profile_for_user(user_id: int, ctx: Any) -> Mapping[str, str | None]:
        return {}

    from services.api.app.diabetes import learning_onboarding as onboarding_utils

    monkeypatch.setattr(onboarding_utils.profiles, "get_profile_for_user", fake_get_profile_for_user)

    async def fake_generate_step_text(*_a: object, **_k: object) -> str:
        return "first"

    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")

    def fake_generate_learning_plan(first_step: str | None = None) -> list[str]:
        return [first_step or "first", "second"]

    monkeypatch.setattr(learning_handlers, "generate_learning_plan", fake_generate_learning_plan)

    monkeypatch.setattr(learning_handlers, "add_lesson_log", _noop)
    monkeypatch.setattr(learning_handlers.plans_repo, "get_active_plan", _noop)
    monkeypatch.setattr(learning_handlers.plans_repo, "create_plan", _noop)
    monkeypatch.setattr(learning_handlers.plans_repo, "update_plan", _noop)
    monkeypatch.setattr(learning_handlers.progress_service, "upsert_progress", _noop)
    async def _start(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", _start
    )

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            learning_onboarding.onboarding_reply,
        )
    )
    await app.initialize()

    user = User(id=1, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")

    def _msg(mid: int, text: str, *, entities: list[MessageEntity] | None = None) -> Message:
        m = Message(
            message_id=mid,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            text=text,
            entities=entities,
        )
        m._bot = bot
        return m

    await app.process_update(Update(update_id=1, message=_msg(1, "/learn", entities=[MessageEntity("bot_command", 0, 6)])))
    await app.process_update(Update(update_id=2, message=_msg(2, "49")))
    await app.process_update(Update(update_id=3, message=_msg(3, "2")))
    await app.process_update(Update(update_id=4, message=_msg(4, "0")))

    plan = fake_generate_learning_plan("first")
    assert app.user_data[1]["learning_plan"] == plan
    assert bot.sent[-1] == "first"

    await app.shutdown()
