import logging
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if __name__ == "__main__" and __package__ is None:  # pragma: no cover - setup for direct execution
    # Ensure repository root is the first entry so that the correct `services`
    # package is imported when running this file directly.  There is another
    # third-party package named ``services`` installed in the environment which
    # would otherwise take precedence and cause `ModuleNotFoundError`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "services.api.app"

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from .diabetes.services.db import (
    HistoryRecord as HistoryRecordDB,
    Timezone as TimezoneDB,
    run_db,
)
from .legacy import router
from .schemas.history import HistoryRecordSchema

logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(router)

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


@app.get("/ui/{full_path:path}", include_in_schema=False)
async def catch_all_ui(full_path: str) -> FileResponse:
    requested_file = (UI_DIR / full_path).resolve()
    try:
        requested_file.relative_to(UI_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404) from exc
    if requested_file.is_file():
        return FileResponse(requested_file)
    return FileResponse(UI_DIR / "index.html")


@app.get("/ui", include_in_schema=False)
async def catch_root_ui() -> FileResponse:
    return await catch_all_ui("")


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
    except SQLAlchemyError as exc:  # pragma: no cover - database errors
        logger.exception("database error while saving history")
        raise HTTPException(status_code=500, detail="database error") from exc
    except RuntimeError as exc:  # pragma: no cover - misconfiguration
        logger.exception("database not initialized")
        raise HTTPException(status_code=500, detail="database not initialized") from exc
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover - convenience for manual execution
    import uvicorn

    uvicorn.run("services.api.app.main:app", host="0.0.0.0", port=8000)

