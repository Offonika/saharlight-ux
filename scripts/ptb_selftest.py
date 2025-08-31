# scripts/ptb_selftest.py
"""
Мини-самотест PTB+APScheduler.
Проверяет импорт, версии, текущую TZ APScheduler и планирует одноразовую задачу через 10 секунд.
Запускать в том же venv, что и бот.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telegram.ext import ApplicationBuilder

async def main():
    print("== PTB/APScheduler selftest ==")
    app = (
        ApplicationBuilder()
        .token("DUMMY_TOKEN_WILL_NOT_CONNECT")  # токен не требуется для локального JobQueue
        .build()
    )
    # Зададим TZ как в проде (важно: это конфигурируется в вашем main.py)
    app.job_queue.scheduler.configure(timezone=ZoneInfo("Europe/Moscow"))
    print("APScheduler timezone:", app.job_queue.scheduler.timezone)

    # Планируем задачу через 10 секунд и смотрим, не падает ли со старым параметром timezone
    when = datetime.now(tz=timezone.utc) + timedelta(seconds=10)
    def _probe(ctx): print(f"[{datetime.now()}] PROBE JOB fired ok")
    app.job_queue.run_once(lambda ctx: _probe(ctx), when=when)  # без timezone=...

    # Печать текущих джобов из APScheduler
    for j in app.job_queue.scheduler.get_jobs():
        print("Job:", j)

    # Короткий run, чтобы джоба успела отработать
    async with app:
        print("Starting short run (15s)...")
        await asyncio.sleep(15)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
