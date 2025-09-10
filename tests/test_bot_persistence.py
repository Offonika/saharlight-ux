from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from telegram.ext import Application, CallbackContext, ExtBot

from services.api import rest_client
from services.bot.main import build_persistence


@pytest.mark.asyncio
async def test_tg_init_data_persisted_after_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    persistence_path = tmp_path / "data.pkl"

    async def dummy_initialize(self: ExtBot) -> None:
        return None

    async def dummy_shutdown(self: ExtBot) -> None:
        return None

    monkeypatch.setattr(ExtBot, "initialize", dummy_initialize)
    monkeypatch.setattr(ExtBot, "shutdown", dummy_shutdown)

    monkeypatch.setenv("BOT_PERSISTENCE_PATH", str(persistence_path))
    persistence1 = build_persistence()
    app1 = Application.builder().token("TOKEN").persistence(persistence1).build()
    await app1.initialize()

    app1.user_data[1]["tg_init_data"] = "abc"
    await app1.persistence.update_user_data(1, app1.user_data[1])
    await app1.persistence.flush()

    persistence2 = build_persistence()
    app2 = Application.builder().token("TOKEN").persistence(persistence2).build()
    await app2.initialize()

    ctx2: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]] = CallbackContext(app2, user_id=1)
    assert ctx2.user_data["tg_init_data"] == "abc"


@pytest.mark.asyncio
async def test_tg_init_data_persisted_and_used_by_rest_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    persistence_path = tmp_path / "data.pkl"

    async def dummy_initialize(self: ExtBot) -> None:
        return None

    async def dummy_shutdown(self: ExtBot) -> None:
        return None

    monkeypatch.setattr(ExtBot, "initialize", dummy_initialize)
    monkeypatch.setattr(ExtBot, "shutdown", dummy_shutdown)

    monkeypatch.setenv("BOT_PERSISTENCE_PATH", str(persistence_path))
    persistence1 = build_persistence()
    app1 = Application.builder().token("TOKEN").persistence(persistence1).build()
    await app1.initialize()
    app1.user_data[1]["tg_init_data"] = "secret"
    await app1.persistence.update_user_data(1, app1.user_data[1])
    await app1.persistence.flush()

    persistence2 = build_persistence()
    app2 = Application.builder().token("TOKEN").persistence(persistence2).build()
    await app2.initialize()

    ctx2: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]] = CallbackContext(app2, user_id=1)
    assert ctx2.user_data["tg_init_data"] == "secret"

    class Settings:
        api_url = "http://example"
        internal_api_key: str | None = None

    class DummyResponse:
        def raise_for_status(self) -> None:  # noqa: D401
            return None

        def json(self) -> dict[str, object]:  # noqa: D401
            return {}

    class DummyClient:
        def __init__(self, capture: dict[str, object]) -> None:
            self.capture = capture

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
            return None

        async def get(
            self, url: str, headers: dict[str, str] | None = None
        ) -> DummyResponse:
            self.capture["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr(rest_client, "get_settings", lambda: Settings())
    captured: dict[str, object] = {}
    monkeypatch.setattr(httpx, "AsyncClient", lambda: DummyClient(captured))
    await rest_client.get_json("/foo", ctx=ctx2)
    assert captured["headers"]["Authorization"] == "tg secret"
