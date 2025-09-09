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

    async def fake_generate_step_text(
        profile: Mapping[str, str | None],
        slug: str,
        step_idx: int,
        prev_summary: str | None,
    ) -> str:
        nonlocal captured_profile
        captured_profile = profile
        return "шаг1"

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

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
    assert bot.sent[-1] == "шаг1"
    assert all(
        title not in s and "Выберите тему" not in s and "Доступные темы" not in s
        for s in bot.sent
    )
    assert captured_profile == {
        "age_group": "adult",
        "diabetes_type": "T2",
        "learning_level": "novice",
    }

    await app.shutdown()


@pytest.mark.asyncio()
async def test_restart_skips_onboarding(monkeypatch: pytest.MonkeyPatch) -> None:
    """After restart user should not be asked onboarding questions again."""

    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    async def fake_generate_step_text(
        profile: Mapping[str, str | None],
        slug: str,
        step_idx: int,
        prev_summary: str | None,
    ) -> str:
        return "шаг1"

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    profile_db: SimpleNamespace | None = None

    async def fake_get_learning_profile(user_id: int) -> SimpleNamespace | None:
        return profile_db

    async def fake_create_plan(user_id: int, _course_id: int, plan: list[str]) -> int:
        return 1

    async def fake_get_active_plan(user_id: int) -> None:
        return None

    async def fake_update_plan(plan_id: int, plan_json: list[str]) -> None:
        return None

    async def fake_upsert_progress(
        user_id: int, plan_id: int, data: Mapping[str, Any]
    ) -> None:
        return None

    async def fake_get_progress(user_id: int, plan_id: int) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)
    monkeypatch.setattr(
        learning_handlers, "get_learning_profile", fake_get_learning_profile
    )
    monkeypatch.setattr(learning_handlers.plans_repo, "create_plan", fake_create_plan)
    monkeypatch.setattr(
        learning_handlers.plans_repo, "get_active_plan", fake_get_active_plan
    )
    monkeypatch.setattr(learning_handlers.plans_repo, "update_plan", fake_update_plan)
    monkeypatch.setattr(
        learning_handlers.progress_service, "upsert_progress", fake_upsert_progress
    )
    monkeypatch.setattr(
        learning_handlers.progress_service, "get_progress", fake_get_progress
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

    # initial onboarding
    await app.process_update(
        Update(
            update_id=1,
            message=_msg(1, "/learn", entities=[MessageEntity("bot_command", 0, 6)]),
        )
    )
    await app.process_update(Update(update_id=2, message=_msg(2, "49")))
    await app.process_update(Update(update_id=3, message=_msg(3, "2")))
    await app.process_update(Update(update_id=4, message=_msg(4, "0")))

    profile_db = SimpleNamespace(**app.user_data[1]["learn_profile_overrides"])

    await app.shutdown()
    bot.sent.clear()

    # restart application
    app2 = Application.builder().bot(bot).build()
    app2.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app2.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND, learning_onboarding.onboarding_reply
        )
    )
    await app2.initialize()

    await app2.process_update(
        Update(
            update_id=10,
            message=_msg(5, "/learn", entities=[MessageEntity("bot_command", 0, 6)]),
        )
    )

    assert bot.sent == ["шаг1"]
    assert app2.user_data[1].get("learning_onboarded") is True

    await app2.shutdown()
