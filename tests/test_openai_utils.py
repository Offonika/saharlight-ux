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
