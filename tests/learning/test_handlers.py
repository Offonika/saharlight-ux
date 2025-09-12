from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import cast
import re

import pytest
from telegram import (
    Bot,
    CallbackQuery,
    Chat,
    Message,
    MessageEntity,
    Update,
    User,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers, dynamic_tutor


class DummyBot(Bot):
    def __init__(self) -> None:
        super().__init__(token="123:ABC")
        object.__setattr__(self, "_sent", [])

    @property
    def sent(self) -> list[str]:
        return self._sent  # type: ignore[attr-defined]

    async def initialize(self) -> None:  # pragma: no cover - setup
        self._me = User(id=0, is_bot=True, first_name="Bot", username="bot")
        self._bot = self
        self._initialized = True

    @property
    def username(self) -> str:  # pragma: no cover - simple property
        return "bot"

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

    async def answer_callback_query(
        self, callback_query_id: str, **kwargs: object
    ) -> bool:
        return True


@pytest.mark.asyncio
async def test_learning_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", True)
    steps = iter(["step1? extra?question", "step2?? more?"])
    call_count = 0

    async def fake_check_user_answer(
        profile: object, topic: str, answer: str, last_step_text: str
    ) -> tuple[bool, str]:
        return True, "<b>✅ feedback</b>"

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    async def fake_start_lesson(user_id: int, topic_slug: str) -> object:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int, lesson_id: int, profile: object, prev_summary: str | None = None
    ) -> tuple[str, bool]:
        nonlocal call_count
        call_count += 1
        text = next(steps)
        if call_count == 1:
            return dynamic_tutor.ensure_single_question(text), False
        return text, False

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )

    async def fake_ensure_overrides(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app.add_handler(CallbackQueryHandler(learning_handlers.lesson_callback))
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND), learning_handlers.lesson_answer_handler
        )
    )
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

    cb_message = Message(message_id=2, date=datetime.now(), chat=chat, from_user=user)
    cb_message._bot = bot
    callback = CallbackQuery(
        id="1",
        from_user=user,
        chat_instance="1",
        data="lesson:xe_basics",
        message=cb_message,
    )
    callback._bot = bot
    await app.process_update(Update(update_id=2, callback_query=callback))

    ans_msg = Message(
        message_id=3, date=datetime.now(), chat=chat, from_user=user, text="42"
    )
    ans_msg._bot = bot
    await app.process_update(Update(update_id=3, message=ans_msg))
    plan = learning_handlers.generate_learning_plan("step1? extraquestion")
    assert bot.sent == [
        "Выберите тему:",
        "Доступные темы:",
        f"\U0001f5fa План обучения\n{learning_handlers.pretty_plan(plan)}",
        "step1? extraquestion",
        "✅ feedback\n\n—\n\nstep2? more",
    ]
    assert len(re.findall(r"\?", bot.sent[3])) == 1
    assert len(re.findall(r"\?", bot.sent[4])) == 1

    await app.shutdown()


@pytest.mark.asyncio
async def test_learning_flow_empty_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", True)
    steps = iter(["step1", "step2"])

    async def fake_create_learning_chat_completion(**kwargs: object) -> str:
        return "***"

    monkeypatch.setattr(
        dynamic_tutor,
        "create_learning_chat_completion",
        fake_create_learning_chat_completion,
    )

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    async def fake_start_lesson(user_id: int, topic_slug: str) -> object:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int, lesson_id: int, profile: object, prev_summary: str | None = None
    ) -> tuple[str, bool]:
        return next(steps), False

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )

    async def fake_ensure_overrides(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app.add_handler(CallbackQueryHandler(learning_handlers.lesson_callback))
    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND), learning_handlers.lesson_answer_handler
        )
    )
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

    cb_message = Message(message_id=2, date=datetime.now(), chat=chat, from_user=user)
    cb_message._bot = bot
    callback = CallbackQuery(
        id="1",
        from_user=user,
        chat_instance="1",
        data="lesson:xe_basics",
        message=cb_message,
    )
    callback._bot = bot
    await app.process_update(Update(update_id=2, callback_query=callback))

    ans_msg = Message(
        message_id=3, date=datetime.now(), chat=chat, from_user=user, text="42"
    )
    ans_msg._bot = bot
    await app.process_update(Update(update_id=3, message=ans_msg))
    plan = learning_handlers.generate_learning_plan("step1")
    assert bot.sent == [
        "Выберите тему:",
        "Доступные темы:",
        f"\U0001f5fa План обучения\n{learning_handlers.pretty_plan(plan)}",
        "step1",
        dynamic_tutor.BUSY_MESSAGE,
    ]

    await app.shutdown()


@pytest.mark.asyncio
async def test_static_mode_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[tuple[object, object]] = []

    async def fake_learn_command(update: object, context: object) -> None:
        called.append((update, context))

    monkeypatch.setattr(
        learning_handlers,
        "settings",
        SimpleNamespace(learning_content_mode="static", learning_mode_enabled=True),
    )
    monkeypatch.setattr(
        learning_handlers, "_static_learn_command", fake_learn_command
    )

    upd = cast(Update, SimpleNamespace(message=object()))
    ctx = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())
    await learning_handlers.learn_command(upd, ctx)

    assert called == [(upd, ctx)]
