from __future__ import annotations

from typing import Any, cast

from services.api.app.diabetes.utils.jobs import _remove_jobs


class RemovableJob:
    def __init__(self, name: str) -> None:
        self.id = name
        self.name = name
        self.removed = False

    def remove(self) -> None:  # pragma: no cover - simple
        self.removed = True


class NonRemovableJob:
    def __init__(self, name: str) -> None:
        self.id = name
        self.name = name


class SchedulableJob:
    def __init__(self, name: str) -> None:
        self.id = name
        self.name = name
        self.scheduled = False

    def schedule_removal(self) -> None:  # pragma: no cover - simple
        self.scheduled = True


class DummyScheduler:
    def __init__(self, jobs: dict[str, object]) -> None:
        self.jobs = jobs
        self.removed: list[str] = []

    def get_job(self, job_id: str) -> object | None:
        return self.jobs.get(job_id)

    def remove_job(self, job_id: str) -> None:
        if job_id in self.jobs:
            self.removed.append(job_id)
            del self.jobs[job_id]
        else:  # pragma: no cover - defensive
            raise KeyError(job_id)


class DummyQueue:
    def __init__(self, jobs: list[object], scheduler: DummyScheduler) -> None:
        self._jobs = jobs
        self.scheduler = scheduler

    def get_jobs_by_name(self, name: str) -> list[object]:
        return [j for j in self._jobs if getattr(j, "name", None) == name]

    def jobs(self) -> list[object]:
        return list(self._jobs)


def test_remove_jobs_covers_variants() -> None:
    job1 = RemovableJob("reminder_1")
    job2 = NonRemovableJob("reminder_1_after")
    job3 = SchedulableJob("reminder_1_snooze_extra")
    scheduler = DummyScheduler({job1.id: job1, job2.id: job2, job3.id: job3})
    queue = DummyQueue([job1, job2, job3], scheduler)

    removed = _remove_jobs(cast(Any, queue), "reminder_1")

    assert removed == 3
    assert job1.removed is True
    assert "reminder_1_after" not in scheduler.jobs
    assert job3.scheduled is True or job3.id not in scheduler.jobs
