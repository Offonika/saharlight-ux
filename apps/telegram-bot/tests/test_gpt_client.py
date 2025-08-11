import logging
import threading
import time
from types import SimpleNamespace

import pytest
from openai import OpenAIError

from diabetes import gpt_client


def test_get_client_thread_safe(monkeypatch):
    fake_client = object()
    call_count = 0

    def fake_get_openai_client():
        nonlocal call_count
        time.sleep(0.01)
        call_count += 1
        return fake_client

    monkeypatch.setattr(gpt_client, "get_openai_client", fake_get_openai_client)
    monkeypatch.setattr(gpt_client, "_client", None)
    results = []

    def worker():
        results.append(gpt_client._get_client())

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert call_count == 1
    assert all(r is fake_client for r in results)


def test_send_message_openaierror(monkeypatch, caplog):
    def raise_error(**kwargs):
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
            gpt_client.send_message(thread_id="t", content="hi")

    assert any("Failed to create message" in r.message for r in caplog.records)


def test_create_thread_openaierror(monkeypatch, caplog):
    def raise_error():
        raise OpenAIError("boom")

    fake_client = SimpleNamespace(beta=SimpleNamespace(threads=SimpleNamespace(create=raise_error)))

    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(OpenAIError):
            gpt_client.create_thread()

    assert any("Failed to create thread" in r.message for r in caplog.records)


def test_send_message_upload_error_keeps_file(tmp_path, monkeypatch):
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    def raise_upload(*_, **__):
        raise OpenAIError("boom")

    fake_client = SimpleNamespace(files=SimpleNamespace(create=raise_upload))
    monkeypatch.setattr(gpt_client, "_get_client", lambda: fake_client)

    with pytest.raises(OpenAIError):
        gpt_client.send_message(thread_id="t", image_path=str(img))

    assert img.exists()


def test_send_message_empty_string_preserved(tmp_path, monkeypatch):
    img = tmp_path / "img.jpg"
    img.write_bytes(b"data")

    captured = {}

    def fake_files_create(file, purpose):
        return SimpleNamespace(id="f1")

    def fake_messages_create(*, thread_id, role, content):
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

    gpt_client.send_message(thread_id="t", content="", image_path=str(img))
    assert captured["content"][1]["text"] == ""
    assert not img.exists()
