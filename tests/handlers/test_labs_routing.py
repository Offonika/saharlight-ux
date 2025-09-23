from __future__ import annotations

import asyncio
import datetime as dt
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Bot, Chat, Message, PhotoSize, Update, User
from telegram.ext import Application

from services.api.app.diabetes import labs_handlers
from services.api.app.diabetes.handlers import photo_handlers, registration


class DummyBot(Bot):
    """Bot stub that skips network interactions."""

    def __init__(self) -> None:
        super().__init__(token="123:ABC")

    async def initialize(self) -> None:  # pragma: no cover - setup helper
        self._me = User(id=0, is_bot=True, first_name="Bot", username="bot")
        self._bot = self
        self._bot_user = self._me
        self._initialized = True


def _photo_update(bot: Bot, user_id: int, update_id: int) -> Update:
    user = User(id=user_id, is_bot=False, first_name="User")
    chat = Chat(id=user_id, type="private")
    photo = PhotoSize(
        file_id=f"photo-{update_id}",
        file_unique_id=f"photo-{update_id}-u",
        width=10,
        height=10,
        file_size=100,
    )
    message = Message(
        message_id=update_id,
        date=dt.datetime.now(dt.timezone.utc),
        chat=chat,
        from_user=user,
        photo=[photo],
    )
    message._bot = bot
    return Update(update_id=update_id, message=message)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")


@pytest.fixture
async def app_with_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Application, AsyncMock, AsyncMock]:
    settings = SimpleNamespace(
        learning_mode_enabled=False,
        assistant_mode_timeout_sec=60,
    )
    monkeypatch.setattr("services.api.app.config.reload_settings", lambda: settings)
    monkeypatch.setattr(registration, "register_profile_handlers", lambda app: None)
    monkeypatch.setattr(registration, "register_reminder_handlers", lambda app: None)
    monkeypatch.setattr(
        "services.api.app.assistant.repositories.logs.cleanup_old_logs",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "services.api.app.assistant.services.memory_service.cleanup_old_memory",
        AsyncMock(),
    )

    labs_mock: AsyncMock = AsyncMock(return_value=labs_handlers.END)
    photo_mock: AsyncMock = AsyncMock(return_value=labs_handlers.END)
    monkeypatch.setattr(labs_handlers, "labs_handler", labs_mock)
    monkeypatch.setattr(registration, "labs_handler", labs_mock)
    monkeypatch.setattr(photo_handlers, "photo_handler", photo_mock)

    bot = DummyBot()
    app = Application.builder().bot(bot).build()
    registration.register_handlers(app)

    async with app:
        await app.start()
        try:
            yield app, labs_mock, photo_mock
        finally:
            await app.stop()


@pytest.mark.asyncio
async def test_photo_update_without_labs_flags_goes_to_photo_handler(
    app_with_handlers: tuple[Application, AsyncMock, AsyncMock],
) -> None:
    app, labs_mock, photo_mock = app_with_handlers
    update = _photo_update(app.bot, user_id=111, update_id=1)

    await app.process_update(update)
    await asyncio.sleep(0)

    labs_mock.assert_not_awaited()
    photo_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_labs_mode_photo_uses_labs_handler(
    app_with_handlers: tuple[Application, AsyncMock, AsyncMock],
) -> None:
    app, labs_mock, photo_mock = app_with_handlers
    user_id = 222
    app._user_data[user_id]["waiting_labs"] = True
    update = _photo_update(app.bot, user_id=user_id, update_id=2)

    await app.process_update(update)
    await asyncio.sleep(0)

    labs_mock.assert_awaited_once()
    photo_mock.assert_not_awaited()
