# scripts/ptb_selftest_offline.py
# Фикс: колбэк теперь async, работает без реального токена и без сети.
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from telegram.ext import ApplicationBuilder, ContextTypes


async def probe(_ctx: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[{datetime.now(tz=timezone.utc):%H:%M:%S} UTC] PROBE JOB fired ok")


async def main() -> None:
    app = ApplicationBuilder().token("TEST:TOKEN").build()
    assert app.job_queue is not None
    app.job_queue.scheduler.configure(timezone=ZoneInfo("Europe/Moscow"))
    print("APScheduler timezone:", app.job_queue.scheduler.timezone)
    app.job_queue.scheduler.start(paused=False)

    when = datetime.now(tz=timezone.utc) + timedelta(seconds=5)
    app.job_queue.run_once(probe, when=when, name="probe_offline")

    await asyncio.sleep(7)
    app.job_queue.scheduler.shutdown(wait=False)

if __name__ == "__main__":
    asyncio.run(main())
