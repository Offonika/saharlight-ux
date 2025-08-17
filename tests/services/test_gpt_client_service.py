import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from openai import OpenAIError

from services.api.app.config import settings
from services.api.app.diabetes.services import gpt_client


@pytest.mark.asyncio
async def test_send_message_requires_payload() -> None:
    with pytest.raises(ValueError):
        await gpt_client.send_message(thread_id="t")


@pytest.mark.asyncio
async def test_send_message_missing_assistant_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake_client = SimpleNamespace(
        beta=SimpleNamespace(threads=SimpleNamespace(messages=SimpleNamespace(create=lambda **_: None)))
    )
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await gpt_client.send_message(thread_id="t", content="hi")

    assert any("OPENAI_ASSISTANT_ID is not set" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_message_run_error_retry(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    call_count = 0

    def fake_runs_create(*_: Any, **__: Any) -> SimpleNamespace:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OpenAIError("boom")
        return SimpleNamespace(id="r2")

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(create=lambda **_: None),
                runs=SimpleNamespace(create=fake_runs_create),
            )
        )
    )
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst")

    with caplog.at_level(logging.DEBUG):
        for _ in range(2):
            try:
                run = await gpt_client.send_message(thread_id="t", content="hi")
            except OpenAIError:
                continue
            break

    assert call_count == 2
    assert run.id == "r2"
    assert any("Failed to create run" in r.message for r in caplog.records)
    assert any("Run r2 started" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_message_cleanup_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    def fake_files_create(file: Any, purpose: str) -> SimpleNamespace:
        return SimpleNamespace(id="f1")

    def fake_messages_create(**_: Any) -> None:
        return None

    def fake_runs_create(**_: Any) -> SimpleNamespace:
        return SimpleNamespace(id="r1")

    fake_client = SimpleNamespace(
        files=SimpleNamespace(create=fake_files_create),
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(create=fake_messages_create),
                runs=SimpleNamespace(create=fake_runs_create),
            )
        ),
    )
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst")

    def fake_remove(_: str) -> None:
        raise OSError("nope")

    monkeypatch.setattr(gpt_client, "os", SimpleNamespace(remove=fake_remove))

    with caplog.at_level(logging.WARNING):
        await gpt_client.send_message(thread_id="t", image_path=str(img))

    assert img.exists()
    assert any("Failed to delete" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_create_thread_retry(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    call_count = 0

    def fake_threads_create() -> SimpleNamespace:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OpenAIError("boom")
        return SimpleNamespace(id="t1")

    fake_client = SimpleNamespace(beta=SimpleNamespace(threads=SimpleNamespace(create=fake_threads_create)))
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)

    with caplog.at_level(logging.ERROR):
        for _ in range(2):
            try:
                thread_id = await gpt_client.create_thread()
            except OpenAIError:
                continue
            break

    assert call_count == 2
    assert thread_id == "t1"
    assert any("Failed to create thread" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_message_image_open_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(gpt_client, "_get_client", lambda: SimpleNamespace())

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OSError):
            await gpt_client.send_message(thread_id="t", image_path="missing.jpg")

    assert any("Failed to read" in r.message for r in caplog.records)
