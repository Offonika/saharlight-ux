from __future__ import annotations

from services.api.app.diabetes.utils.jobs import _remove_jobs, dbg_jobs_dump


class _Job:
    def __init__(
        self,
        queue: _JobQueue,
        *,
        name: str | None = None,
        job_id: str | None = None,
        has_remove: bool = False,
        has_schedule_removal: bool = False,
    ) -> None:
        self.queue = queue
        self.name = name
        self.id = job_id
        if has_remove:

            def remove() -> None:
                queue.remove_job(self)

            self.remove = remove  # type: ignore[assignment]
        if has_schedule_removal:

            def schedule_removal() -> None:
                queue.remove_job(self)

            self.schedule_removal = schedule_removal  # type: ignore[assignment]


class _Scheduler:
    def __init__(self, queue: _JobQueue) -> None:
        self.queue = queue

    def remove_job(self, job_id: str) -> None:
        self.queue.remove_job_by_id(job_id)

    def get_job(self, job_id: str) -> _Job | None:
        for job in self.queue._jobs:
            if getattr(job, "id", None) == job_id:
                return job
        return None


class _JobQueue:
    def __init__(self) -> None:
        self._jobs: list[_Job] = []
        self.scheduler = _Scheduler(self)

    def get_jobs_by_name(self, name: str) -> list[_Job]:
        result: list[_Job] = []
        for job in self._jobs:
            jname = getattr(job, "name", None)
            if jname is not None and jname.startswith(name):
                result.append(job)
        return result

    def remove_job(self, job: _Job) -> None:
        try:
            self._jobs.remove(job)
        except ValueError:
            pass

    def remove_job_by_id(self, job_id: str) -> None:
        self._jobs = [j for j in self._jobs if getattr(j, "id", None) != job_id]

    def jobs(self) -> list[_Job]:
        return list(self._jobs)


def test_remove_jobs() -> None:
    jq = _JobQueue()
    jq._jobs.extend(
        [
            _Job(jq, job_id="reminder_1"),
            _Job(jq, name="reminder_1", has_remove=True),
            _Job(jq, name="reminder_1_after", has_schedule_removal=True),
            _Job(jq, name="reminder_1_snooze", has_schedule_removal=True),
            _Job(jq, name="reminder_1_extra", job_id="reminder_1_extra"),
            _Job(jq, job_id="reminder_1_foo"),
        ]
    )

    before = dbg_jobs_dump(jq)
    assert len(before) == 6
    assert ("reminder_1", None) in before

    removed = _remove_jobs(jq, "reminder_1")

    assert removed == 6
    assert dbg_jobs_dump(jq) == []
    assert jq.get_jobs_by_name("reminder_1") == []
    assert jq.jobs() == []
