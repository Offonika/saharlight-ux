import logging

import httpx
import pytest

from services.api import rest_client


class DummyCtx:
    def __init__(self, init_data: str | None = None) -> None:
        self.user_data = {"tg_init_data": init_data} if init_data is not None else {}


class DummyResponse:
    def __init__(self) -> None:
        self._json: dict[str, object] = {}

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict[str, object]:
        return self._json


class DummyClient:
    def __init__(self, capture: dict[str, object]) -> None:
        self.capture = capture

    async def __aenter__(self) -> "DummyClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(
        self, url: str, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        self.capture["headers"] = headers
        return DummyResponse()


@pytest.mark.asyncio
async def test_get_json_uses_tg_init_data(monkeypatch: pytest.MonkeyPatch) -> None:
    class Settings:
        api_url = "http://example"
        internal_api_key: str | None = None

    monkeypatch.setattr(rest_client, "get_settings", lambda: Settings())
    captured: dict[str, object] = {}
    monkeypatch.setattr(httpx, "AsyncClient", lambda: DummyClient(captured))
    await rest_client.get_json("/foo", ctx=DummyCtx("abc"))
    assert captured["headers"]["Authorization"] == "tg abc"


@pytest.mark.asyncio
async def test_get_json_prefers_internal_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class Settings:
        api_url = "http://example"
        internal_api_key = "secret"

    monkeypatch.setattr(rest_client, "get_settings", lambda: Settings())
    captured: dict[str, object] = {}
    monkeypatch.setattr(httpx, "AsyncClient", lambda: DummyClient(captured))
    await rest_client.get_json("/foo", ctx=DummyCtx("abc"))
    assert captured["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_get_json_logs_missing_auth(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class Settings:
        api_url = "http://example"
        internal_api_key: str | None = None

    monkeypatch.setattr(rest_client, "get_settings", lambda: Settings())
    captured: dict[str, object] = {}
    monkeypatch.setattr(httpx, "AsyncClient", lambda: DummyClient(captured))
    caplog.set_level(logging.WARNING)
    await rest_client.get_json("/foo", ctx=DummyCtx())
    assert "No Authorization header" in caplog.text
