import asyncio
import json
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import aiofiles

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .schemas.history import HistoryRecordSchema

logger = logging.getLogger(__name__)

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parents[2] / "webapp"
UI_DIR = BASE_DIR / "ui" / "dist"
if not UI_DIR.exists():
    UI_DIR = BASE_DIR / "ui"
UI_DIR = UI_DIR.resolve()
TIMEZONE_FILE = Path(__file__).resolve().parent / "timezone.txt"
HISTORY_FILE = Path(__file__).resolve().parent / "history.json"
history_lock = asyncio.Lock()


class Timezone(BaseModel):
    tz: str


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}


@app.get("/timezone")
async def get_timezone() -> dict:
    if not TIMEZONE_FILE.exists():
        raise HTTPException(status_code=404, detail="timezone not set")
    try:
        tz = TIMEZONE_FILE.read_text(encoding="utf-8").strip()
        ZoneInfo(tz)
    except (OSError, ZoneInfoNotFoundError) as exc:
        raise HTTPException(status_code=500, detail="invalid timezone file") from exc
    return {"tz": tz}


@app.put("/timezone")
async def put_timezone(data: Timezone) -> dict:
    try:
        ZoneInfo(data.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone") from exc

    async with aiofiles.tempfile.NamedTemporaryFile(
        "w", dir=TIMEZONE_FILE.parent, delete=False, encoding="utf-8"
    ) as tmp:
        await tmp.write(data.tz)
        await tmp.flush()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, os.fsync, tmp.fileno())

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, os.replace, tmp.name, TIMEZONE_FILE)
    return {"status": "ok"}


app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")


@app.post("/api/history")
async def post_history(data: HistoryRecordSchema) -> dict:
    """Save or update a history record.

    Records are stored in a local JSON file. If a record with the same ``id``
    exists, it will be replaced.
    """

    try:
        async with history_lock:
            if HISTORY_FILE.exists():
                async with aiofiles.open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    content = await f.read()
                records = json.loads(content) if content else []
                if not isinstance(records, list):  # pragma: no cover - corrupted file
                    records = []
            else:
                records = []

            for idx, rec in enumerate(records):
                if rec.get("id") == data.id:
                    records[idx] = data.model_dump()
                    break
            else:
                records.append(data.model_dump())

            async with aiofiles.tempfile.NamedTemporaryFile(
                "w", dir=HISTORY_FILE.parent, delete=False, encoding="utf-8"
            ) as tmp:
                await tmp.write(json.dumps(records, ensure_ascii=False, indent=2))
                await tmp.flush()
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, os.fsync, tmp.fileno())
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, os.replace, tmp.name, HISTORY_FILE)
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("failed to save history")
        raise HTTPException(status_code=500, detail="failed to save history") from exc
    return {"status": "ok"}
