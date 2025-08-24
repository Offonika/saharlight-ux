import pytest
from telegram import BotCommand
from telegram.ext import Application

from services.bot.configure_commands import COMMANDS, configure_commands


@pytest.mark.asyncio
async def test_configure_commands_sets_my_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Application.builder().token("123:ABC").build()

    store: list[BotCommand] = []

    async def fake_set(self: object, commands: list[BotCommand]) -> None:
        store[:] = commands

    async def fake_get(self: object) -> list[BotCommand]:
        return store

    monkeypatch.setattr(app.bot.__class__, "set_my_commands", fake_set)
    monkeypatch.setattr(app.bot.__class__, "get_my_commands", fake_get)

    await configure_commands(app)
    try:
        assert await app.bot.get_my_commands() == COMMANDS
    finally:
        await app.shutdown()
