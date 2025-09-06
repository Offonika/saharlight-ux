from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import cast

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

from services.api.app.diabetes import learning_handlers


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

    async def answer_callback_query(self, callback_query_id: str, **kwargs: object) -> bool:
        return True


@pytest.mark.asyncio
async def test_learning_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    steps = iter(["step1", "step2"])

    async def fake_generate_step_text(*args: object, **kwargs: object) -> str:
        return next(steps)

    async def fake_check_user_answer(*args: object, **kwargs: object) -> str:
        return "feedback"

    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)
    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)

    async def fake_ensure_overrides(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app.add_handler(CallbackQueryHandler(learning_handlers.lesson_callback))
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), learning_handlers.lesson_answer_handler)
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

    ans_msg = Message(message_id=3, date=datetime.now(), chat=chat, from_user=user, text="42")
    ans_msg._bot = bot
    await app.process_update(Update(update_id=3, message=ans_msg))

    assert bot.sent == ["Выберите тему:", "Доступные темы:", "step1", "feedback", "step2"]

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
    monkeypatch.setattr(learning_handlers.legacy_handlers, "learn_command", fake_learn_command)

    upd = cast(Update, SimpleNamespace(message=object()))
    ctx = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())
    await learning_handlers.learn_command(upd, ctx)

    assert called == [(upd, ctx)]
