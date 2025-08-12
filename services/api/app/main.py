import logging
import os
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parents[2] / "webapp"
UI_DIR = (BASE_DIR / "ui").resolve()
TIMEZONE_FILE = Path(__file__).resolve().parent / "timezone.txt"


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
    with tempfile.NamedTemporaryFile(
        "w", dir=TIMEZONE_FILE.parent, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(data.tz)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.replace(tmp.name, TIMEZONE_FILE)
    return {"status": "ok"}


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")
