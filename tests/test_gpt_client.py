import threading
import time

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
