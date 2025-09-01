from __future__ import annotations

from typing import Any

from tests.conftest import _DummyJobQueue


def _callback(context: Any) -> None:
    return None


def test_run_repeating_schedules_job() -> None:
    job_queue = _DummyJobQueue()
    job_queue.run_repeating(
        _callback,
        interval=5,
        data={"a": 1},
        name="job",
        timezone="UTC",
    )
    jobs = job_queue.get_jobs_by_name("job")
    assert len(jobs) == 1
    assert jobs[0].name == "job"
    assert jobs[0].data == {"a": 1}
