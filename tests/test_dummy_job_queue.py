from __future__ import annotations

from datetime import timezone
from unittest.mock import patch

from tests.conftest import _DummyJobQueue


def test_run_repeating_schedules_job() -> None:
    jq = _DummyJobQueue()
    with patch.object(jq.scheduler, "add_job", wraps=jq.scheduler.add_job) as spy:
        jq.run_repeating(
            lambda: None,
            interval=5,
            data={"a": 1},
            name="test",
            timezone=timezone.utc,
        )
    spy.assert_called_once()
    assert spy.call_args.kwargs["trigger"] == "interval"
    jobs = jq.get_jobs_by_name("test")
    assert len(jobs) == 1
    assert jobs[0].data == {"a": 1}
