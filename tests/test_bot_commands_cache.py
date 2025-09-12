from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import services.bot.main as main


class DummyRedis:
    def __init__(self, value: str | None) -> None:
        self.value = value
        self.set_called = False
        self.ttl: timedelta | None = None

    async def get(self, key: str) -> str | None:
        assert key == main.REDIS_KEY
        return self.value

    async def set(self, key: str, value: str, *, ex: timedelta) -> None:
        self.set_called = True
        self.value = value
        self.ttl = ex

    async def close(self) -> None:
        return None


class DummyBot:
    def __init__(self) -> None:
        self.called = False

    async def set_my_commands(self, commands: list[object]) -> None:
        self.called = True


@pytest.mark.asyncio
async def test_skip_recent_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = DummyBot()
    recent = datetime.now(timezone.utc).isoformat()
    redis_stub = DummyRedis(recent)
    monkeypatch.setattr(main.redis, "from_url", lambda *a, **kw: redis_stub)
    await main.update_commands_if_needed(bot)
    assert not bot.called
    assert not redis_stub.set_called


@pytest.mark.asyncio
async def test_set_commands_and_store_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = DummyBot()
    old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    redis_stub = DummyRedis(old)
    monkeypatch.setattr(main.redis, "from_url", lambda *a, **kw: redis_stub)
    await main.update_commands_if_needed(bot)
    assert bot.called
    assert redis_stub.set_called
    assert redis_stub.ttl and redis_stub.ttl.total_seconds() > 24 * 3600
