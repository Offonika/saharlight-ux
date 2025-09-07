from __future__ import annotations

from datetime import datetime
import re

import pytest
from telegram import Bot, Chat, Message, MessageEntity, ReplyKeyboardMarkup, Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.handlers import learning_handlers as legacy_learning_handlers
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT, LEARN_BUTTON_OLD_TEXT


class DummyBot(Bot):
    def __init__(self) -> None:  # pragma: no cover - simple setup
        super().__init__(token="123:ABC")
        object.__setattr__(self, "_texts", [])
        object.__setattr__(self, "_markups", [])

    @property
    def texts(self) -> list[str]:  # pragma: no cover - simple property
        return self._texts  # type: ignore[attr-defined]

    @property
    def markups(self) -> list[object | None]:  # pragma: no cover - simple property
        return self._markups  # type: ignore[attr-defined]

    async def initialize(self) -> None:  # pragma: no cover - setup
        self._me = User(id=0, is_bot=True, first_name="Bot", username="bot")  # type: ignore[attr-defined]
        self._bot = self
        self._initialized = True

    @property
    def username(self) -> str:  # pragma: no cover - simple property
        return "bot"

    async def send_message(self, chat_id: int, text: str, **kwargs: object) -> Message:
        msg = Message(
            message_id=len(self.texts) + 1,
            date=datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            from_user=self._me,
            text=text,
            reply_markup=kwargs.get("reply_markup"),
        )
        msg._bot = self
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))
        return msg


@pytest.mark.asyncio
async def test_keyboard_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", True)
    async def fake_ensure_overrides(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(CommandHandler("learn", learning_handlers.learn_command))
    app.add_handler(CommandHandler("exit", learning_handlers.exit_command))
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

    exit_msg = Message(
        message_id=2,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text="/exit",
        entities=[MessageEntity(type="bot_command", offset=0, length=5)],
    )
    exit_msg._bot = bot
    await app.process_update(Update(update_id=2, message=exit_msg))

    first_markup = bot.markups[0]
    assert isinstance(first_markup, ReplyKeyboardMarkup)
    assert any(
        LEARN_BUTTON_TEXT == button.text for row in first_markup.keyboard for button in row
    )
    assert isinstance(bot.markups[-1], ReplyKeyboardMarkup)

    await app.shutdown()


@pytest.mark.asyncio
async def test_old_button_invokes_learn(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"v": False}

    async def fake_learn(*_args: object, **_kwargs: object) -> None:
        called["v"] = True

    monkeypatch.setattr(legacy_learning_handlers, "learn_command", fake_learn)

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    app.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(
                rf"^(?:{re.escape(LEARN_BUTTON_TEXT)}|{re.escape(LEARN_BUTTON_OLD_TEXT)})$"
            ),
            legacy_learning_handlers.on_learn_button,
        )
    )
    await app.initialize()

    user = User(id=1, is_bot=False, first_name="T")
    chat = Chat(id=1, type="private")
    msg = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text=LEARN_BUTTON_OLD_TEXT,
    )
    msg._bot = bot
    await app.process_update(Update(update_id=1, message=msg))

    assert called["v"] is True

    await app.shutdown()
