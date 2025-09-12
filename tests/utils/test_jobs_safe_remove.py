import logging

import pytest

from services.api.app.diabetes.utils.jobs import _safe_remove


class _FailingJob:
    id = "1"
    name = "bad"

    def remove(self) -> None:  # pragma: no cover - simple mock
        raise ValueError("boom")


def test_safe_remove_unknown_exception(caplog: pytest.LogCaptureFixture) -> None:
    job = _FailingJob()
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError):
            _safe_remove(job)
    assert "remove() raised unexpected error" in caplog.text
