from datetime import datetime
from types import SimpleNamespace
from typing import Mapping

import pytest
from telegram import Bot, Chat, Message, MessageEntity, Update, User
from telegram.ext import Application, CommandHandler

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.planner import generate_learning_plan, pretty_plan


def test_generate_and_pretty_plan() -> None:
    plan = generate_learning_plan({"learning_level": "novice"})
    # novice plan always starts from basics-of-diabetes
    assert plan[0] == "basics-of-diabetes"
    rendered = pretty_plan(plan, 1)
    assert "2. 👉 Хлебные единицы" in rendered


class DummyBot(Bot):
    def __init__(self) -> None:  # pragma: no cover - simple init
        super().__init__(token="123:ABC")
        object.__setattr__(self, "_sent", [])

    @property
    def sent(self) -> list[str]:
        return self._sent  # type: ignore[attr-defined]

    async def initialize(self) -> None:  # pragma: no cover - setup helper
        self._me = User(id=0, is_bot=True, first_name="bot")
        self._bot = self
        self._initialized = True

    async def send_message(self, chat_id: int, text: str, **kwargs: object) -> Message:
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

    @property
    def username(self) -> str:  # pragma: no cover - simple attribute
        return "bot"


@pytest.mark.asyncio
async def test_plan_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", False)

    async def fake_generate_step_text(*_: object, **__: object) -> str:
        return "step"

    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

    async def fake_start(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    async def fake_next(
        user_id: int, lesson_id: int, profile: Mapping[str, str | None]
    ) -> tuple[str, bool]:
        return "step", False

    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next)

    async def fake_ensure_overrides(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app.add_handler(CommandHandler("plan", learning_handlers.plan_command))
    app.add_handler(CommandHandler("skip", learning_handlers.skip_command))
    await app.initialize()

    user = User(id=1, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")

    learn_msg = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="/learn",
        entities=[MessageEntity(type="bot_command", offset=0, length=6)],
    )
    learn_msg._bot = bot
    await app.process_update(Update(update_id=1, message=learn_msg))

    plan_msg = Message(
        message_id=2,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="/plan",
        entities=[MessageEntity(type="bot_command", offset=0, length=5)],
    )
    plan_msg._bot = bot
    await app.process_update(Update(update_id=2, message=plan_msg))

    skip_msg = Message(
        message_id=3,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="/skip",
        entities=[MessageEntity(type="bot_command", offset=0, length=5)],
    )
    skip_msg._bot = bot
    await app.process_update(Update(update_id=3, message=skip_msg))

    # first message is first step, second is plan, third is next topic step
    assert bot.sent[0] == "step"
    assert "👉" in bot.sent[1]
    assert bot.sent[2] == "step"

    await app.shutdown()
