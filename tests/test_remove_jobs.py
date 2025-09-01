from __future__ import annotations

from services.api.app.diabetes.utils.jobs import _remove_jobs


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


class _JobQueue:
    def __init__(self) -> None:
        self.jobs: list[_Job] = []
        self.scheduler = _Scheduler(self)

    def get_jobs_by_name(self, name: str) -> list[_Job]:
        result: list[_Job] = []
        for job in self.jobs:
            jname = getattr(job, "name", None)
            jid = getattr(job, "id", None)
            if (jname is not None and jname.startswith(name)) or (
                isinstance(jid, str) and jid.startswith(name)
            ):
                result.append(job)
        return result

    def remove_job(self, job: _Job) -> None:
        try:
            self.jobs.remove(job)
        except ValueError:
            pass

    def remove_job_by_id(self, job_id: str) -> None:
        self.jobs = [j for j in self.jobs if getattr(j, "id", None) != job_id]


def test_remove_jobs() -> None:
    jq = _JobQueue()
    jq.jobs.extend(
        [
            _Job(jq, job_id="reminder_1"),
            _Job(jq, name="reminder_1", has_remove=True),
            _Job(jq, name="reminder_1_after", has_schedule_removal=True),
            _Job(jq, name="reminder_1_snooze", has_schedule_removal=True),
        ]
    )

    removed = _remove_jobs(jq, "reminder_1")

    assert removed == 4
    assert jq.get_jobs_by_name("reminder_1") == []
    assert jq.jobs == []
