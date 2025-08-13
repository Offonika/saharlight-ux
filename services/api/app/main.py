import logging
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .diabetes.services.db import (
    HistoryRecord as HistoryRecordDB,
    Timezone as TimezoneDB,
    run_db,
)
from .schemas.history import HistoryRecordSchema

logger = logging.getLogger(__name__)

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parents[2] / "webapp"
UI_DIR = BASE_DIR / "ui" / "dist"
if not UI_DIR.exists():
    UI_DIR = BASE_DIR / "ui"
UI_DIR = UI_DIR.resolve()


class Timezone(BaseModel):
    tz: str


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}


@app.get("/timezone")
async def get_timezone() -> dict:
    def _get_timezone(session):
        return session.get(TimezoneDB, 1)

    tz_row = await run_db(_get_timezone)
    if not tz_row:
        raise HTTPException(status_code=404, detail="timezone not set")
    try:
        ZoneInfo(tz_row.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=500, detail="invalid timezone entry") from exc
    return {"tz": tz_row.tz}


@app.put("/timezone")
async def put_timezone(data: Timezone) -> dict:
    try:
        ZoneInfo(data.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone") from exc

    def _save_timezone(session, tz: str):
        obj = session.get(TimezoneDB, 1)
        if obj is None:
            obj = TimezoneDB(id=1, tz=tz)
            session.add(obj)
        else:
            obj.tz = tz
        session.commit()

    await run_db(_save_timezone, data.tz)
    return {"status": "ok"}


app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")


@app.post("/api/history")
async def post_history(data: HistoryRecordSchema) -> dict:
    """Save or update a history record in the database."""

    def _save_history(session, record: HistoryRecordSchema) -> None:
        obj = session.get(HistoryRecordDB, record.id)
        if obj:
            obj.date = record.date
            obj.time = record.time
            obj.sugar = record.sugar
            obj.carbs = record.carbs
            obj.bread_units = record.breadUnits
            obj.insulin = record.insulin
            obj.notes = record.notes
            obj.type = record.type
        else:
            obj = HistoryRecordDB(
                id=record.id,
                date=record.date,
                time=record.time,
                sugar=record.sugar,
                carbs=record.carbs,
                bread_units=record.breadUnits,
                insulin=record.insulin,
                notes=record.notes,
                type=record.type,
            )
            session.add(obj)
        session.commit()

    try:
        await run_db(_save_history, data)
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("failed to save history")
        raise HTTPException(status_code=500, detail="failed to save history") from exc
    return {"status": "ok"}

