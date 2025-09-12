import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from services.api.app import config
from services.api.app.diabetes.utils import openai_utils

_original_get_openai_client = openai_utils.get_openai_client
_original_get_async_openai_client = openai_utils.get_async_openai_client


@pytest.fixture(autouse=True)
def _restore_openai_utils(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_utils, "get_openai_client", _original_get_openai_client)
    monkeypatch.setattr(openai_utils, "get_async_openai_client", _original_get_async_openai_client)


def test_get_openai_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_utils, "_http_client", {})
    fake_settings = SimpleNamespace(openai_api_key="", openai_proxy=None, openai_assistant_id=None)
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    with pytest.raises(RuntimeError):
        openai_utils.get_openai_client()


@pytest.mark.asyncio
async def test_get_openai_client_uses_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_http_client = Mock()
    http_client_mock = Mock(return_value=fake_http_client)
    openai_mock = Mock()

    fake_settings = SimpleNamespace(openai_api_key="key", openai_proxy="http://proxy", openai_assistant_id=None)
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(openai_utils, "_http_client", {})
    monkeypatch.setattr(httpx, "Client", http_client_mock)
    monkeypatch.setattr(openai_utils, "OpenAI", openai_mock)

    client = openai_utils.get_openai_client()

    http_client_mock.assert_called_once_with(proxies="http://proxy")
    fake_http_client.close.assert_not_called()
    openai_mock.assert_called_once_with(api_key="key", http_client=fake_http_client)
    assert client is openai_mock.return_value

    await openai_utils.dispose_http_client()
    fake_http_client.close.assert_called_once()


def test_get_openai_client_logs_assistant(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    openai_mock = Mock()
    fake_settings = SimpleNamespace(openai_api_key="key", openai_proxy=None, openai_assistant_id="assistant")
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(openai_utils, "_http_client", {})
    monkeypatch.setattr(openai_utils, "OpenAI", openai_mock)

    with caplog.at_level(logging.INFO):
        openai_utils.get_openai_client()

    assert any("Using assistant: assistant" in r.message for r in caplog.records)


def test_get_openai_client_without_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    openai_mock = Mock()
    http_client_mock = Mock()

    fake_settings = SimpleNamespace(openai_api_key="key", openai_proxy=None, openai_assistant_id=None)
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(openai_utils, "_http_client", {})
    monkeypatch.setattr(openai_utils, "OpenAI", openai_mock)
    monkeypatch.setattr(httpx, "Client", http_client_mock)

    client = openai_utils.get_openai_client()

    http_client_mock.assert_not_called()
    openai_mock.assert_called_once_with(api_key="key", http_client=None)
    assert client is openai_mock.return_value


@pytest.mark.asyncio
async def test_http_client_lock_used(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyLock:
        def __init__(self) -> None:
            self.entered = False
            self.exited = False

        def __enter__(self) -> None:
            self.entered = True

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            self.exited = True

    dummy_lock = DummyLock()
    fake_http_client = Mock()
    fake_settings = SimpleNamespace(openai_api_key="key", openai_proxy="http://proxy", openai_assistant_id=None)

    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(openai_utils, "_http_client_lock", dummy_lock)
    monkeypatch.setattr(openai_utils, "_http_client", {})
    monkeypatch.setattr(httpx, "Client", Mock(return_value=fake_http_client))
    monkeypatch.setattr(openai_utils, "OpenAI", Mock())

    openai_utils.get_openai_client()
    assert dummy_lock.entered and dummy_lock.exited

    dummy_lock.entered = False
    dummy_lock.exited = False

    await openai_utils.dispose_http_client()
    assert dummy_lock.entered and dummy_lock.exited


def test_get_async_openai_client_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(openai_utils, "_async_http_client", {})
    fake_settings = SimpleNamespace(openai_api_key="", openai_proxy=None, openai_assistant_id=None)
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    with pytest.raises(RuntimeError):
        openai_utils.get_async_openai_client()


@pytest.mark.asyncio
async def test_get_async_openai_client_uses_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_async_client = Mock()
    fake_async_client.aclose = AsyncMock()
    async_client_mock = Mock(return_value=fake_async_client)

    openai_mock = Mock()

    fake_settings = SimpleNamespace(openai_api_key="key", openai_proxy="http://proxy", openai_assistant_id=None)
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(openai_utils, "_async_http_client", {})

    monkeypatch.setattr(httpx, "AsyncClient", async_client_mock)
    monkeypatch.setattr(openai_utils, "AsyncOpenAI", openai_mock)
    monkeypatch.setattr(openai_utils, "_http_client", {})

    client = openai_utils.get_async_openai_client()

    async_client_mock.assert_called_once_with(proxies="http://proxy")
    openai_mock.assert_called_once_with(api_key="key", http_client=fake_async_client)
    assert client is openai_mock.return_value

    await openai_utils.dispose_http_client()
    fake_async_client.aclose.assert_awaited_once()
    assert openai_utils._async_http_client == {}


@pytest.mark.asyncio
async def test_dispose_http_client_resets_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_http_client = Mock()
    fake_async_client = Mock()
    fake_async_client.aclose = AsyncMock()

    monkeypatch.setattr(openai_utils, "_http_client", {"p": fake_http_client})
    monkeypatch.setattr(openai_utils, "_async_http_client", {"p": fake_async_client})

    await openai_utils.dispose_http_client()

    fake_http_client.close.assert_called_once()
    fake_async_client.aclose.assert_awaited_once()
    assert openai_utils._http_client == {}
    assert openai_utils._async_http_client == {}


@pytest.mark.asyncio
async def test_openai_client_ctx_disposes(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_http_client = Mock()
    http_client_mock = Mock(return_value=fake_http_client)
    openai_mock = Mock()

    fake_settings = SimpleNamespace(openai_api_key="key", openai_proxy="http://proxy", openai_assistant_id=None)
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(openai_utils, "_http_client", {})
    monkeypatch.setattr(httpx, "Client", http_client_mock)
    monkeypatch.setattr(openai_utils, "OpenAI", openai_mock)

    async with openai_utils.openai_client_ctx() as client:
        assert client is openai_mock.return_value

    fake_http_client.close.assert_called_once()
    assert openai_utils._http_client == {}


@pytest.mark.asyncio
async def test_openai_client_ctx_disposes_with_running_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispose_mock = AsyncMock()
    monkeypatch.setattr(openai_utils, "dispose_http_client", dispose_mock)
    monkeypatch.setattr(openai_utils, "get_openai_client", Mock())

    run_mock = Mock(side_effect=RuntimeError("asyncio.run should not be called"))
    monkeypatch.setattr(asyncio, "run", run_mock)

    async with openai_utils.openai_client_ctx():
        pass

    dispose_mock.assert_awaited_once()
    run_mock.assert_not_called()


@pytest.mark.asyncio
async def test_async_openai_client_ctx_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_async_client = Mock()
    fake_async_client.aclose = AsyncMock()
    async_client_mock = Mock(return_value=fake_async_client)
    openai_mock = Mock()

    fake_settings = SimpleNamespace(openai_api_key="key", openai_proxy="http://proxy", openai_assistant_id=None)
    monkeypatch.setattr(config, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(openai_utils, "_async_http_client", {})
    monkeypatch.setattr(openai_utils, "_http_client", {})
    monkeypatch.setattr(httpx, "AsyncClient", async_client_mock)
    monkeypatch.setattr(openai_utils, "AsyncOpenAI", openai_mock)

    async with openai_utils.async_openai_client_ctx() as client:
        assert client is openai_mock.return_value

    fake_async_client.aclose.assert_awaited_once()
    assert openai_utils._async_http_client == {}


@pytest.mark.asyncio
async def test_async_openai_client_ctx_logs_dispose_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake_client = object()
    monkeypatch.setattr(openai_utils, "get_async_openai_client", Mock(return_value=fake_client))
    dispose_mock = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(openai_utils, "dispose_http_client", dispose_mock)

    with caplog.at_level(logging.ERROR):
        async with openai_utils.async_openai_client_ctx() as client:
            assert client is fake_client

    dispose_mock.assert_awaited_once()
    assert any("Failed to dispose HTTP client" in record.message for record in caplog.records)


def test_dispose_http_client_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_http_client = Mock()
    monkeypatch.setattr(openai_utils, "_http_client", {"p": fake_http_client})
    monkeypatch.setattr(openai_utils, "_async_http_client", {})

    openai_utils._dispose_http_client_sync()

    fake_http_client.close.assert_called_once()
    assert openai_utils._http_client == {}


def test_dispose_http_client_sync_uses_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyRunner:
        def __init__(self) -> None:
            self.run = Mock()
            self.close = Mock()

        def __enter__(self) -> "DummyRunner":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            self.close()

    dummy_runner = DummyRunner()
    runner_factory = Mock(return_value=dummy_runner)
    monkeypatch.setattr(asyncio, "Runner", runner_factory)
    monkeypatch.setattr(asyncio, "get_running_loop", Mock(side_effect=RuntimeError()))

    dispose_mock = AsyncMock()
    monkeypatch.setattr(openai_utils, "dispose_http_client", dispose_mock)
    monkeypatch.setattr(openai_utils, "_http_client", {})
    monkeypatch.setattr(openai_utils, "_async_http_client", {})

    openai_utils._dispose_http_client_sync()

    runner_factory.assert_called_once_with()
    dispose_mock.assert_called_once_with()
    dummy_runner.run.assert_called_once()
    args, _ = dummy_runner.run.call_args
    assert asyncio.iscoroutine(args[0])
    dummy_runner.close.assert_called_once()


@pytest.mark.asyncio
async def test_build_http_client_returns_separate_clients_for_each_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client1 = Mock()
    fake_client2 = Mock()
    client_mock = Mock(side_effect=[fake_client1, fake_client2])
    monkeypatch.setattr(httpx, "Client", client_mock)
    monkeypatch.setattr(openai_utils, "_http_client", {})

    client_a = openai_utils._build_http_client("http://proxy1", False)
    client_b = openai_utils._build_http_client("http://proxy2", False)

    assert client_a is fake_client1
    assert client_b is fake_client2
    assert openai_utils._build_http_client("http://proxy1", False) is client_a

    await openai_utils.dispose_http_client()
    fake_client1.close.assert_called_once()
    fake_client2.close.assert_called_once()


@pytest.mark.asyncio
async def test_build_async_http_client_returns_separate_clients_for_each_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_async_client1 = Mock()
    fake_async_client1.aclose = AsyncMock()
    fake_async_client2 = Mock()
    fake_async_client2.aclose = AsyncMock()
    async_client_mock = Mock(side_effect=[fake_async_client1, fake_async_client2])

    monkeypatch.setattr(httpx, "AsyncClient", async_client_mock)
    monkeypatch.setattr(openai_utils, "_async_http_client", {})
    monkeypatch.setattr(openai_utils, "_http_client", {})

    client_a = openai_utils._build_http_client("http://proxy1", True)
    client_b = openai_utils._build_http_client("http://proxy2", True)

    assert client_a is fake_async_client1
    assert client_b is fake_async_client2
    assert openai_utils._build_http_client("http://proxy1", True) is client_a

    await openai_utils.dispose_http_client()
    fake_async_client1.aclose.assert_awaited_once()
    fake_async_client2.aclose.assert_awaited_once()
