import builtins
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services.bot import main


@pytest.mark.asyncio
async def test_post_init_without_redis(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "redis.asyncio":
            raise ModuleNotFoundError
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(main, "redis", main.redis_stub)

    def fake_from_url(*args: object, **kwargs: object) -> None:
        raise AssertionError("redis.from_url should not be called")

    monkeypatch.setattr(main.redis_stub, "from_url", fake_from_url)
    monkeypatch.setattr(main, "menu_button_post_init", AsyncMock())
    monkeypatch.setattr(
        "services.api.app.diabetes.handlers.assistant_menu.post_init",
        AsyncMock(),
    )

    bot = AsyncMock()
    app = SimpleNamespace(bot=bot, job_queue=None)

    await main.post_init(app)

    bot.set_my_commands.assert_awaited_once_with(main.commands)
