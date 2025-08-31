from inspect import isawaitable

from telegram.ext import JobQueue


async def test_shutdown_jobqueue() -> None:
    job_queue = JobQueue()
    job_queue.scheduler.start()
    result = job_queue.scheduler.shutdown(wait=False)
    if isawaitable(result):
        await result
    executor = getattr(job_queue, "executor", None)
    if executor is None:
        executor = getattr(job_queue, "_executor", None)
    executor.shutdown(wait=False)

