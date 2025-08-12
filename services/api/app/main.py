import logging
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
    return {"tz": TIMEZONE_FILE.read_text(encoding="utf-8").strip()}


@app.put("/timezone")
async def put_timezone(data: Timezone) -> dict:
    try:
        ZoneInfo(data.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone") from exc
    TIMEZONE_FILE.write_text(data.tz, encoding="utf-8")
    return {"status": "ok"}


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")
