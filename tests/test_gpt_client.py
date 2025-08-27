import logging
import threading
import time
from types import SimpleNamespace

import pytest
from openai import OpenAIError

from services.api.app.diabetes.services import gpt_client
from services.api.app.config import settings
from typing import Any


def test_get_client_thread_safe(monkeypatch: Any) -> None:
    fake_client = object()
    call_count = 0

    def fake_get_openai_client() -> None:
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
async def test_send_message_openaierror(monkeypatch: Any, caplog: Any) -> None:
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

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OpenAIError):
            await gpt_client.send_message(thread_id="t", content="hi")

    assert any("Failed to create message" in r.message for r in caplog.records)


def test_create_thread_openaierror(monkeypatch: Any, caplog: Any) -> None:
    def raise_error() -> None:
        raise OpenAIError("boom")

    fake_client = SimpleNamespace(beta=SimpleNamespace(threads=SimpleNamespace(create=raise_error)))

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OpenAIError):
            gpt_client.create_thread()

    assert any("Failed to create thread" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_message_upload_error_keeps_file(tmp_path: Any, monkeypatch: Any) -> None:
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    def raise_upload(*_: Any, **__: Any) -> None:
        raise OpenAIError("boom")

    fake_client = SimpleNamespace(files=SimpleNamespace(create=raise_upload))
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)

    with pytest.raises(OpenAIError):
        await gpt_client.send_message(thread_id="t", image_path=str(img))

    assert img.exists()


@pytest.mark.asyncio
async def test_send_message_empty_string_preserved(tmp_path: Any, monkeypatch: Any) -> None:
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    captured = {}

    def fake_files_create(file: Any, purpose: Any) -> None:
        return SimpleNamespace(id="f1")

    def fake_messages_create(*, thread_id: Any, role: Any, content: Any) -> None:
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

    await gpt_client.send_message(thread_id="t", content="", image_path=str(img))
    assert captured["content"][1]["text"] == ""
    assert not img.exists()
