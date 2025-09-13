import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Coroutine

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
    called = False

    def fake_get_client() -> None:
        nonlocal called
        called = True
        raise AssertionError("_get_client should not be called")

    monkeypatch.setattr(gpt_client, "_get_client", fake_get_client)
    monkeypatch.setattr(
        gpt_client.config,
        "get_settings",
        lambda: SimpleNamespace(openai_assistant_id=""),
    )

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await gpt_client.send_message(thread_id="t", content="hi")

    assert not called
    assert any("OPENAI_ASSISTANT_ID is not set" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_send_message_run_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fake_messages_create(**_: Any) -> None:
        return None

    def fake_runs_create(**_: Any) -> None:
        return None

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(create=fake_messages_create),
                runs=SimpleNamespace(create=fake_runs_create),
            )
        )
    )
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)
    monkeypatch.setattr(settings, "openai_assistant_id", "asst")

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError):
            await gpt_client.send_message(thread_id="t", content="hi")

    assert any("Run creation returned None" in r.message for r in caplog.records)
    assert not any(
        r.levelno == logging.DEBUG and "Run" in r.message for r in caplog.records
    )


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
async def test_send_message_no_cleanup_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
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

    called = False

    def fake_remove(_: str) -> None:
        nonlocal called
        called = True
        raise OSError("nope")

    monkeypatch.setattr(
        gpt_client, "os", SimpleNamespace(remove=fake_remove), raising=False
    )

    with caplog.at_level(logging.WARNING):
        await gpt_client.send_message(thread_id="t", image_bytes=b"data")

    assert not called
    assert not any("Failed to delete" in r.message for r in caplog.records)


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

    fake_client = SimpleNamespace(
        beta=SimpleNamespace(threads=SimpleNamespace(create=fake_threads_create))
    )
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
async def test_send_message_path_and_bytes_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    with pytest.raises(ValueError):
        await gpt_client.send_message(
            thread_id="t", image_path=str(img), image_bytes=b"data"
        )


def test_create_thread_sync_no_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create_thread() -> str:
        return "tid"

    called: dict[str, bool] = {"run": False}

    def fake_run(coro: Coroutine[Any, Any, str]) -> str:
        called["run"] = True
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr(asyncio, "run", fake_run)
    monkeypatch.setattr(
        asyncio,
        "get_running_loop",
        lambda: (_ for _ in ()).throw(RuntimeError("no loop")),
    )
    monkeypatch.setattr(gpt_client, "create_thread", fake_create_thread)

    assert gpt_client.create_thread_sync() == "tid"
    assert called["run"]


def test_create_thread_sync_running_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create_thread() -> str:
        return "tid"

    called: dict[str, bool] = {"create_task": False, "run_until_complete": False}

    def fake_create_task(coro: Coroutine[Any, Any, str]) -> Coroutine[Any, Any, str]:
        called["create_task"] = True
        return coro

    class DummyLoop:
        def run_until_complete(self, coro: Coroutine[Any, Any, str]) -> str:
            called["run_until_complete"] = True
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: DummyLoop())
    monkeypatch.setattr(gpt_client, "create_thread", fake_create_thread)

    assert gpt_client.create_thread_sync() == "tid"
    assert called["create_task"]
    assert called["run_until_complete"]
