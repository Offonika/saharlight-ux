import asyncio
import logging
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

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
async def test_upload_image_file(tmp_path: Path) -> None:
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    def fake_files_create(file: Any, purpose: str) -> SimpleNamespace:
        assert purpose == "vision"
        assert file.read() == b"data"
        return SimpleNamespace(id="f1")

    fake_client = SimpleNamespace(files=SimpleNamespace(create=fake_files_create))
    file = await gpt_client._upload_image_file(fake_client, str(img))
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
