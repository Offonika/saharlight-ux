import asyncio
import logging
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from services.api.app import config
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from openai import OpenAIError
from services.api.app.diabetes.services import gpt_client
from services.api.app.config import settings


def test_get_client_thread_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = object()
    call_count = 0

    def fake_get_openai_client() -> object:
        nonlocal call_count
        time.sleep(0.01)
        call_count += 1
        return fake_client

    monkeypatch.setattr(gpt_client, "get_openai_client", fake_get_openai_client)
    monkeypatch.setattr(gpt_client, "_client", None)
    results = []

    def worker() -> None:
        results.append(gpt_client._get_client())

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert call_count == 1
    assert all(r is fake_client for r in results)


def test_get_async_client_multiple_loops(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyAsyncClient:
        async def close(self) -> None:
            return None

    fake_client = DummyAsyncClient()
    call_count = 0

    def fake_get_async_openai_client() -> object:
        nonlocal call_count
        call_count += 1
        return fake_client

    monkeypatch.setattr(
        gpt_client, "get_async_openai_client", fake_get_async_openai_client
    )

    async def run() -> object:
        return await gpt_client._get_async_client()

    asyncio.run(gpt_client.dispose_openai_clients())
    assert asyncio.run(run()) is fake_client
    asyncio.run(gpt_client.dispose_openai_clients())
    assert asyncio.run(run()) is fake_client
    asyncio.run(gpt_client.dispose_openai_clients())

    assert call_count == 2


def test_create_chat_completion_multiple_loops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    class DummyAsyncClient:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create)
            )

        async def _create(self, **_: Any) -> gpt_client.ChatCompletion:
            return gpt_client.ChatCompletion.model_validate(
                {
                    "id": "1",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "gpt",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "ok",
                            },
                        }
                    ],
                }
            )

        async def close(self) -> None:
            return None

    def fake_get_async_openai_client() -> DummyAsyncClient:
        nonlocal call_count
        call_count += 1
        return DummyAsyncClient()

    monkeypatch.setattr(
        gpt_client, "get_async_openai_client", fake_get_async_openai_client
    )
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(openai_api_key="k")
    )

    async def run() -> gpt_client.ChatCompletion:
        return await gpt_client.create_chat_completion(model="gpt", messages=[])

    asyncio.run(gpt_client.dispose_openai_clients())
    assert asyncio.run(run()).choices[0].message.content == "ok"
    asyncio.run(gpt_client.dispose_openai_clients())
    assert asyncio.run(run()).choices[0].message.content == "ok"
    asyncio.run(gpt_client.dispose_openai_clients())
    assert call_count == 2


@pytest.mark.asyncio
async def test_send_message_openaierror(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def raise_error(**kwargs: Any) -> None:
        raise OpenAIError("boom")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(create=raise_error),
                runs=SimpleNamespace(create=lambda **kwargs: None),
            )
        )
    )

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst_test")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OpenAIError):
            await gpt_client.send_message(thread_id="t", content="hi")

    assert any("Failed to create message" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_create_thread_openaierror(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def raise_error() -> None:
        raise OpenAIError("boom")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(threads=SimpleNamespace(create=raise_error))
    )

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OpenAIError):
            await gpt_client.create_thread()

    assert any("Failed to create thread" in r.message for r in caplog.records)


def test_dispose_openai_clients_resets_all_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = Mock()
    fake_async_client = Mock()
    fake_async_client.close = AsyncMock()

    monkeypatch.setattr(gpt_client, "_client", fake_client)
    monkeypatch.setattr(gpt_client, "_async_client", fake_async_client)

    asyncio.run(gpt_client.dispose_openai_clients())

    fake_client.close.assert_called_once()
    fake_async_client.close.assert_awaited_once()
    assert gpt_client._client is None
    assert gpt_client._async_client is None


@pytest.mark.asyncio
async def test_dispose_openai_clients_resets_all_async(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = Mock()
    fake_async_client = Mock()
    fake_async_client.close = AsyncMock()

    monkeypatch.setattr(gpt_client, "_client", fake_client)
    monkeypatch.setattr(gpt_client, "_async_client", fake_async_client)

    await gpt_client.dispose_openai_clients()

    fake_client.close.assert_called_once()
    fake_async_client.close.assert_awaited_once()
    assert gpt_client._client is None
    assert gpt_client._async_client is None


def test_dispose_openai_clients_after_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = Mock()
    fake_async_client = Mock()
    fake_async_client.close = AsyncMock()

    monkeypatch.setattr(gpt_client, "_client", fake_client)
    monkeypatch.setattr(gpt_client, "_async_client", fake_async_client)

    async def create_lock() -> None:
        await gpt_client._get_async_client()

    monkeypatch.setattr(
        gpt_client, "get_async_openai_client", lambda: fake_async_client
    )
    asyncio.run(create_lock())

    asyncio.run(gpt_client.dispose_openai_clients())

    fake_client.close.assert_called_once()
    fake_async_client.close.assert_awaited_once()
    assert gpt_client._client is None
    assert gpt_client._async_client is None
    assert not gpt_client._async_client_locks


@pytest.mark.asyncio
async def test_send_message_upload_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_upload(*_: Any, **__: Any) -> None:
        raise OpenAIError("boom")

    fake_client = SimpleNamespace(files=SimpleNamespace(create=raise_upload))
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst_test")

    with pytest.raises(OpenAIError):
        await gpt_client.send_message(thread_id="t", image_bytes=b"data")


@pytest.mark.asyncio
async def test_send_message_empty_string_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_files_create(file: Any, purpose: str) -> SimpleNamespace:
        return SimpleNamespace(id="f1")

    def fake_messages_create(
        *, thread_id: str, role: str, content: list[dict[str, Any]]
    ) -> None:
        captured["content"] = content

    fake_client = SimpleNamespace(
        files=SimpleNamespace(create=fake_files_create),
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(create=fake_messages_create),
                runs=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(id="r1")),
            )
        ),
    )

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst_test")

    await gpt_client.send_message(thread_id="t", content="", image_bytes=b"data")
    assert captured["content"][1]["text"] == ""


@pytest.mark.asyncio
async def test_create_thread_timeout(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def slow_create() -> None:
        time.sleep(0.05)

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(threads=SimpleNamespace(create=slow_create))
    )

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(gpt_client, "THREAD_CREATION_TIMEOUT", 0.01)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await gpt_client.create_thread()

    assert any("Thread creation timed out" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_message_timeout(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def slow_message_create(
        *, thread_id: str, role: str, content: list[dict[str, Any]]
    ) -> None:
        time.sleep(0.05)

    run_create = Mock()
    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(create=slow_message_create),
                runs=SimpleNamespace(create=run_create),
            )
        )
    )

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst_test")
    monkeypatch.setattr(gpt_client, "MESSAGE_CREATION_TIMEOUT", 0.01)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await gpt_client.send_message(thread_id="t", content="hi")

    run_create.assert_not_called()
    assert any("Message creation timed out" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_message_run_timeout(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    run_create = Mock(side_effect=lambda **_: time.sleep(0.05))
    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(create=lambda **_: None),
                runs=SimpleNamespace(create=run_create),
            )
        )
    )

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst_test")
    monkeypatch.setattr(gpt_client, "RUN_CREATION_TIMEOUT", 0.01)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await gpt_client.send_message(thread_id="t", content="hi")

    assert run_create.call_count == 1
    assert any("Run creation timed out" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_upload_image_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    def fake_files_create(file: Any, purpose: str) -> SimpleNamespace:
        assert purpose == "vision"
        assert file.read() == b"data"
        return SimpleNamespace(id="f1")

    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(photos_dir=str(tmp_path))
    )
    fake_client = SimpleNamespace(files=SimpleNamespace(create=fake_files_create))
    file = await gpt_client._upload_image_file(fake_client, "img.jpg")
    assert file.id == "f1"


@pytest.mark.asyncio
async def test_upload_image_bytes() -> None:
    captured: dict[str, Any] = {}

    def fake_files_create(file: Any, purpose: str) -> SimpleNamespace:
        name, buffer = file
        captured["name"] = name
        captured["data"] = buffer.read()
        return SimpleNamespace(id="f2")

    fake_client = SimpleNamespace(files=SimpleNamespace(create=fake_files_create))
    file = await gpt_client._upload_image_bytes(fake_client, b"payload")
    assert file.id == "f2"
    assert captured == {"name": "image.jpg", "data": b"payload"}


@pytest.mark.asyncio
async def test_create_chat_completion_uses_default_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_create(
        *,
        model: str,
        messages: list[object],
        temperature: float | None,
        max_tokens: int | None,
        timeout: object,
        stream: bool,
    ) -> object:
        captured["timeout"] = timeout
        return SimpleNamespace()

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    async def fake_get_async_client() -> SimpleNamespace:
        return fake_client

    monkeypatch.setattr(gpt_client, "_get_async_client", fake_get_async_client)

    await gpt_client.create_chat_completion(model="gpt", messages=[])

    assert isinstance(captured["timeout"], httpx.Timeout)


@pytest.mark.asyncio
async def test_create_chat_completion_timeout_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fake_create(**_: object) -> None:
        raise httpx.TimeoutException("boom")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    async def fake_get_async_client() -> SimpleNamespace:
        return fake_client

    monkeypatch.setattr(gpt_client, "_get_async_client", fake_get_async_client)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await gpt_client.create_chat_completion(model="m", messages=[])

    assert any(
        "Chat completion request timed out" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_create_chat_completion_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def fake_create(**_: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            request = httpx.Request("POST", "https://api.openai.com/")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError(
                "rate limit", request=request, response=response
            )
        return SimpleNamespace()

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    async def fake_get_async_client() -> SimpleNamespace:
        return fake_client

    monkeypatch.setattr(gpt_client, "_get_async_client", fake_get_async_client)

    await gpt_client.create_chat_completion(model="m", messages=[])

    assert calls == 2


@pytest.mark.asyncio
async def test_create_chat_completion_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(gpt_client, "_async_client", None)
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(openai_api_key=None)
    )

    completion = await gpt_client.create_chat_completion(model="m", messages=[])
    content = completion.choices[0].message.content or ""
    assert "OpenAI API key is not configured" in content


@pytest.mark.asyncio
async def test_create_chat_completion_uses_env_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(
                    return_value=SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))]
                    )
                )
            )
        )
    )

    async_client_mock = AsyncMock(return_value=fake_client)
    monkeypatch.setattr(gpt_client, "_get_async_client", async_client_mock)

    completion = await gpt_client.create_chat_completion(model="m", messages=[])
    content = completion.choices[0].message.content or ""

    assert content == "hi"
    async_client_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_chat_completion_without_chat(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(openai_api_key="key")
    )
    monkeypatch.setattr(gpt_client, "_async_client", None)

    class DummyClient:
        pass

    async def fake_get_async_client() -> DummyClient:
        return DummyClient()

    monkeypatch.setattr(gpt_client, "_get_async_client", fake_get_async_client)

    with caplog.at_level(logging.WARNING):
        completion = await gpt_client.create_chat_completion(model="m", messages=[])

    content = completion.choices[0].message.content or ""
    assert "OpenAI API key is not configured" in content
    assert any("has no attribute 'chat'" in r.message for r in caplog.records)


def test_validate_image_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(photos_dir=str(tmp_path))
    )
    (tmp_path / "img.jpg").write_bytes(b"data")
    resolved = gpt_client._validate_image_path("img.jpg")
    assert resolved == str((tmp_path / "img.jpg").resolve())


def test_validate_image_path_rejects_absolute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "photos_dir", str(tmp_path))
    with pytest.raises(ValueError):
        gpt_client._validate_image_path("/etc/passwd")


def test_validate_image_path_rejects_parent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(settings, "photos_dir", str(tmp_path))
    with pytest.raises(ValueError):
        gpt_client._validate_image_path("../img.jpg")


def test_validate_image_path_rejects_similar_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "photos"
    monkeypatch.setattr(settings, "photos_dir", str(root))
    with pytest.raises(ValueError):
        gpt_client._validate_image_path(str(tmp_path / "photos2" / "img.jpg"))
