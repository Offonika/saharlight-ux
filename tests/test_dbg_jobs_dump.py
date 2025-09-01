from __future__ import annotations

from typing import cast

from services.api.app.diabetes.utils.jobs import DefaultJobQueue, dbg_jobs_dump


class _Job:
    def __init__(self, job_id: str | None, name: str | None) -> None:
        self.id = job_id
        self.name = name


class _JobQueue:
    def __init__(self, jobs: list[_Job]) -> None:
        self._jobs = jobs

    def jobs(self) -> list[_Job]:
        return list(self._jobs)


def test_dbg_jobs_dump() -> None:
    jq = cast(DefaultJobQueue, _JobQueue([_Job("1", "a"), _Job(None, "b")]))
    assert dbg_jobs_dump(jq) == [("1", "a"), (None, "b")]
