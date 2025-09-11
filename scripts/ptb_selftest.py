# scripts/ptb_selftest.py
"""
Мини-самотест PTB+APScheduler.
Проверяет импорт, версии, текущую TZ APScheduler и планирует одноразовую задачу через 10 секунд.
Запускать в том же venv, что и бот.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telegram.ext import ApplicationBuilder

logger = logging.getLogger(__name__)

async def main() -> None:
    logger.info("== PTB/APScheduler selftest ==")
    app = (
        ApplicationBuilder()
        .token("DUMMY_TOKEN_WILL_NOT_CONNECT")  # токен не требуется для локального JobQueue
        .build()
    )
    # Зададим TZ как в проде (важно: это конфигурируется в вашем main.py)
    app.job_queue.scheduler.configure(timezone=ZoneInfo("Europe/Moscow"))
    logger.info("APScheduler timezone: %s", app.job_queue.scheduler.timezone)

    # Планируем задачу через 10 секунд и смотрим, не падает ли со старым параметром timezone
    when = datetime.now(tz=timezone.utc) + timedelta(seconds=10)
    def _probe(ctx: object) -> None:
        logger.info("[%s] PROBE JOB fired ok", datetime.now())
    app.job_queue.run_once(lambda ctx: _probe(ctx), when=when)  # без timezone=...

    # Печать текущих джобов из APScheduler
    for j in app.job_queue.scheduler.get_jobs():
        logger.debug("Job: %s", j)

    # Короткий run, чтобы джоба успела отработать
    async with app:
        logger.info("Starting short run (15s)...")
        await asyncio.sleep(15)
    logger.info("Done.")

if __name__ == "__main__":
    asyncio.run(main())
