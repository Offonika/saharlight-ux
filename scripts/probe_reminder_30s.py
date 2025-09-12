# scripts/probe_reminder_30s.py
# Фикс: читаем токен ещё и из TELEGRAM_TOKEN. Реально шлёт сообщение через 30 секунд.
import asyncio
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from telegram.ext import ApplicationBuilder, ContextTypes

CHAT_ID = int(os.environ.get("CHAT_ID", "448794918"))


async def send_msg(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(tz=timezone.utc)
    await ctx.bot.send_message(CHAT_ID, f"Пробный джоб ✅ (UTC {now:%H:%M:%S})")


async def main() -> None:
    token = (
        os.environ.get("BOT_TOKEN")
        or os.environ.get("TELEGRAM_BOT_TOKEN")
        or os.environ.get("TELEGRAM_TOKEN")
    )
    if not token:
        raise SystemExit("Нет токена: установи BOT_TOKEN/TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN в окружении или .env")

    app = ApplicationBuilder().token(token).build()
    assert app.job_queue is not None
    app.job_queue.scheduler.configure(timezone=ZoneInfo("Europe/Moscow"))
    print("JobQueue TZ:", app.job_queue.scheduler.timezone)

    app.job_queue.run_once(
        send_msg,
        when=datetime.now(tz=timezone.utc) + timedelta(seconds=30),
        name="probe_30s",
    )
    async with app:
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())

