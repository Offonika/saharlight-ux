from __future__ import annotations

from datetime import time
from typing import cast

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.handlers.reminder_jobs import DefaultJobQueue
from services.api.app.diabetes.services.db import Reminder, User as DbUser
from tests.test_schedule_all_queries import DummyJobQueue, _setup_session


def test_schedule_all_removes_legacy_jobs() -> None:
    TestSession, _ = _setup_session()
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        rem = Reminder(
            telegram_id=1,
            type="sugar",
            time=time(8, 0),
            kind="at_time",
            is_enabled=True,
        )
        session.add(rem)
        session.commit()
        rem_id = rem.id

    job_queue = cast(DefaultJobQueue, DummyJobQueue())
    old_job = job_queue.run_daily(lambda *a, **k: None, time(8, 0), name=f"remind_{rem_id}")
    handlers.schedule_all(job_queue)

    assert old_job.removed is True
    assert all(
        j.removed for j in job_queue.jobs() if j.name == f"remind_{rem_id}"
    )
    names = [job.name for job in job_queue.jobs()]
    assert f"reminder_{rem_id}" in names
    new_job = next(j for j in job_queue.jobs() if j.name == f"reminder_{rem_id}")
    assert new_job.removed is False
