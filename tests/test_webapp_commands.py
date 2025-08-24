from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Awaitable, Callable, cast
from urllib.parse import urlparse

import pytest
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ExtBot

from services.api.app.diabetes.handlers import webapp_commands


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.markups: list[InlineKeyboardMarkup | None] = []

    async def reply_text(
        self,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        **_: object,
    ) -> None:
        self.texts.append(text)
        self.markups.append(reply_markup)


def _make_update() -> Update:
    msg = DummyMessage()
    return cast(Update, SimpleNamespace(message=msg))


HandlerType = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]


async def _call_handler(handler: HandlerType) -> InlineKeyboardMarkup:
    update = _make_update()
    context = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())
    await handler(update, context)
    msg = cast(DummyMessage, update.message)
    markup = msg.markups[0]
    assert isinstance(markup, InlineKeyboardMarkup)
    return markup


@pytest.mark.asyncio
async def test_configure_commands_sets_expected_commands() -> None:
    class DummyBot:
        def __init__(self) -> None:
            self.commands: list[object] | None = None

        async def set_my_commands(self, commands: list[object]) -> None:
            self.commands = commands

    bot = cast(ExtBot[None], DummyBot())
    await webapp_commands.configure_commands(bot)
    assert [c.command for c in cast(DummyBot, bot).commands or []] == [
        "history",
        "profile",
        "subscription",
        "reminders",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "path"),
    [
        (webapp_commands.history_command, "/history"),
        (webapp_commands.profile_command, "/profile"),
        (webapp_commands.subscription_command, "/subscription"),
        (webapp_commands.reminders_command, "/api/reminders"),
    ],
)
async def test_commands_reply_with_webapp_url(
    monkeypatch: pytest.MonkeyPatch, handler: HandlerType, path: str
) -> None:
    base_url = "https://example.com"
    monkeypatch.setenv("WEBAPP_URL", base_url)
    config_module = importlib.reload(importlib.import_module("services.api.app.config"))
    webapp_commands.config = config_module
    markup = await _call_handler(handler)
    button = markup.inline_keyboard[0][0]
    assert button.web_app is not None
    assert urlparse(button.web_app.url).path == path
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    config_module = importlib.reload(importlib.import_module("services.api.app.config"))
    webapp_commands.config = config_module
