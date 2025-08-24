import asyncio
import logging
from unittest.mock import Mock

import httpx
import pytest

from services.api.app.config import settings
from services.api.app.diabetes.utils import openai_utils


def test_get_openai_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_utils, "_http_client", None)
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(RuntimeError):
        openai_utils.get_openai_client()


def test_get_openai_client_uses_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_http_client = Mock()
    http_client_mock = Mock(return_value=fake_http_client)
    openai_mock = Mock()

    monkeypatch.setattr(openai_utils, "_http_client", None)
    monkeypatch.setattr(settings, "openai_api_key", "key")
    monkeypatch.setattr(settings, "openai_proxy", "http://proxy")
    monkeypatch.setattr(httpx, "Client", http_client_mock)
    monkeypatch.setattr(openai_utils, "OpenAI", openai_mock)

    client = openai_utils.get_openai_client()

    http_client_mock.assert_called_once_with(proxies="http://proxy")
    fake_http_client.close.assert_not_called()
    openai_mock.assert_called_once_with(api_key="key", http_client=fake_http_client)
    assert client is openai_mock.return_value

    openai_utils.dispose_http_client()
    fake_http_client.close.assert_called_once()


def test_get_openai_client_logs_assistant(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    openai_mock = Mock()
    monkeypatch.setattr(openai_utils, "_http_client", None)
    monkeypatch.setattr(openai_utils, "OpenAI", openai_mock)
    monkeypatch.setattr(settings, "openai_api_key", "key")
    monkeypatch.setattr(settings, "openai_assistant_id", "assistant")
    monkeypatch.setattr(settings, "openai_proxy", None)

    with caplog.at_level(logging.INFO):
        openai_utils.get_openai_client()

    assert any("Using assistant: assistant" in r.message for r in caplog.records)


def test_get_openai_client_without_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    openai_mock = Mock()
    http_client_mock = Mock()

    monkeypatch.setattr(openai_utils, "_http_client", None)
    monkeypatch.setattr(openai_utils, "OpenAI", openai_mock)
    monkeypatch.setattr(settings, "openai_api_key", "key")
    monkeypatch.setattr(settings, "openai_proxy", None)
    monkeypatch.setattr(httpx, "Client", http_client_mock)

    client = openai_utils.get_openai_client()

    http_client_mock.assert_not_called()
    openai_mock.assert_called_once_with(api_key="key", http_client=None)
    assert client is openai_mock.return_value


def test_http_client_lock_used(monkeypatch: pytest.MonkeyPatch) -> None:
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

    monkeypatch.setattr(openai_utils, "_http_client_lock", dummy_lock)
    monkeypatch.setattr(openai_utils, "_http_client", None)
    monkeypatch.setattr(settings, "openai_api_key", "key")
    monkeypatch.setattr(settings, "openai_proxy", "http://proxy")
    monkeypatch.setattr(httpx, "Client", Mock(return_value=fake_http_client))
    monkeypatch.setattr(openai_utils, "OpenAI", Mock())

    openai_utils.get_openai_client()
    assert dummy_lock.entered and dummy_lock.exited

    dummy_lock.entered = False
    dummy_lock.exited = False

    openai_utils.dispose_http_client()
    assert dummy_lock.entered and dummy_lock.exited


def test_dispose_http_client_without_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    closed = False

    class DummyAsyncClient:
        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    client = DummyAsyncClient()
    monkeypatch.setattr(openai_utils, "_async_http_client", client)

    original_run = asyncio.run
    run_called = False

    def run_wrapper(coro: object) -> object:
        nonlocal run_called
        run_called = True
        return original_run(coro)

    monkeypatch.setattr(asyncio, "run", run_wrapper)

    openai_utils.dispose_http_client()

    assert run_called
    assert closed


@pytest.mark.asyncio
async def test_dispose_http_client_with_running_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = False

    class DummyAsyncClient:
        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    client = DummyAsyncClient()
    monkeypatch.setattr(openai_utils, "_async_http_client", client)
    run_mock = Mock()
    monkeypatch.setattr(asyncio, "run", run_mock)

    openai_utils.dispose_http_client()
    await asyncio.sleep(0)

    run_mock.assert_not_called()
    assert closed
