import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from typing import Any

import services.api.app.config as config


def test_reload_settings_thread_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    spans: list[tuple[float, float]] = []

    class SlowSettings(config.Settings):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            start = time.perf_counter()
            time.sleep(0.05)
            super().__init__(*args, **kwargs)
            end = time.perf_counter()
            spans.append((start, end))

    monkeypatch.setattr(config, "Settings", SlowSettings)
    config.reload_settings()
    spans.clear()

    def worker() -> config.Settings:
        return config.reload_settings()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker) for _ in range(5)]
        results = [f.result() for f in futures]

    final_settings = config.get_settings()
    for s in results:
        assert s.app_name == final_settings.app_name

    spans.sort()
    for (start1, end1), (start2, _end2) in zip(spans, spans[1:]):
        assert end1 <= start2
