import logging
import sys
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if __name__ == "__main__" and __package__ is None:  # pragma: no cover - setup for direct execution
    # Ensure repository root is the first entry so that the correct `services`
    # package is imported when running this file directly.  There is another
    # third-party package named ``services`` installed in the environment which
    # would otherwise take precedence and cause `ModuleNotFoundError`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "services.api.app"


from fastapi import Depends, FastAPI, HTTPException, Query

from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .diabetes.services.db import (
    HistoryRecord as HistoryRecordDB,
    Timezone as TimezoneDB,
    User as UserDB,
    run_db,
)
from .diabetes.services.repository import commit
from .legacy import router
from .schemas.history import ALLOWED_HISTORY_TYPES, HistoryRecordSchema, HistoryType
from .schemas.user import UserContext
from .telegram_auth import require_tg_user

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


class WebUser(BaseModel):
    telegram_id: int


class DayStats(BaseModel):
    sugar: float
    breadUnits: float
    insulin: float


class AnalyticsPoint(BaseModel):
    date: str
    sugar: float


def _validate_history_type(value: str, status_code: int = 400) -> HistoryType:
    if value not in ALLOWED_HISTORY_TYPES:
        raise HTTPException(status_code=status_code, detail="invalid history type")
    return cast(HistoryType, value)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/timezone")
async def get_timezone(_: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    def _get_timezone(session: Session) -> TimezoneDB | None:
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
async def put_timezone(data: Timezone, _: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    try:
        ZoneInfo(data.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone") from exc

    tz = data.tz

    def _save_timezone(session: Session) -> None:
        obj = session.get(TimezoneDB, 1)
        if obj is None:
            obj = TimezoneDB(id=1, tz=tz)
            session.add(obj)
        else:
            obj.tz = tz
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    try:
        await run_db(_save_timezone)
    except SQLAlchemyError as exc:  # pragma: no cover - database errors
        logger.exception("database error while saving timezone")
        raise HTTPException(status_code=500, detail="database error") from exc
    return {"status": "ok"}


@app.get("/api/profile/self")
async def profile_self(user: UserContext = Depends(require_tg_user)) -> UserContext:
    return user


@app.get("/api/stats")
async def get_stats(
    telegram_id: int = Query(alias="telegramId"),
    user: UserContext = Depends(require_tg_user),
) -> DayStats:
    if telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")
    return DayStats(sugar=5.7, breadUnits=3, insulin=10)


@app.get("/api/analytics")
async def get_analytics(
    telegram_id: int = Query(alias="telegramId"),
    user: UserContext = Depends(require_tg_user),
) -> list[AnalyticsPoint]:
    if telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")
    return [
        AnalyticsPoint(date="2024-01-01", sugar=5.5),
        AnalyticsPoint(date="2024-01-02", sugar=6.1),
        AnalyticsPoint(date="2024-01-03", sugar=5.8),
        AnalyticsPoint(date="2024-01-04", sugar=6.0),
        AnalyticsPoint(date="2024-01-05", sugar=5.4),
    ]


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


@app.post("/api/user")
async def create_user(
    data: WebUser,
    user: UserContext = Depends(require_tg_user),
) -> dict[str, str]:
    """Ensure a user exists in the database."""

    if data.telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")

    def _create_user(session: Session) -> None:
        db_user = session.get(UserDB, data.telegram_id)
        if db_user is None:
            session.add(UserDB(telegram_id=data.telegram_id, thread_id="webapp"))
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    try:
        await run_db(_create_user)
    except SQLAlchemyError as exc:  # pragma: no cover - database errors
        logger.exception("database error while creating user")
        raise HTTPException(status_code=500, detail="database error") from exc
    return {"status": "ok"}


@app.post("/api/history")
async def post_history(data: HistoryRecordSchema, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    """Save or update a history record in the database."""
    validated_type = _validate_history_type(data.type)

    def _save_history(session: Session) -> None:
        obj = session.get(HistoryRecordDB, data.id)
        if obj:
            if obj.telegram_id != user["id"]:
                raise HTTPException(status_code=403, detail="forbidden")
            obj.date = data.date.isoformat()
            obj.time = data.time.strftime("%H:%M")
            obj.sugar = data.sugar
            obj.carbs = data.carbs
            obj.bread_units = data.breadUnits
            obj.insulin = data.insulin
            obj.notes = data.notes
            obj.type = validated_type
        else:
            obj = HistoryRecordDB(
                id=data.id,
                telegram_id=user["id"],
                date=data.date.isoformat(),
                time=data.time.strftime("%H:%M"),
                sugar=data.sugar,
                carbs=data.carbs,
                bread_units=data.breadUnits,
                insulin=data.insulin,
                notes=data.notes,
                type=validated_type,
            )
            session.add(obj)
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    try:
        await run_db(_save_history)
    except SQLAlchemyError as exc:  # pragma: no cover - database errors
        logger.exception("database error while saving history")
        raise HTTPException(status_code=500, detail="database error") from exc
    except RuntimeError as exc:  # pragma: no cover - misconfiguration
        logger.exception("database not initialized")
        raise HTTPException(status_code=500, detail="database not initialized") from exc
    return {"status": "ok"}


@app.get("/api/history")
async def get_history(user: UserContext = Depends(require_tg_user)) -> list[HistoryRecordSchema]:
    """Return history records for the authenticated user."""

    def _get_history(session: Session) -> list[HistoryRecordDB]:
        return (
            session.query(HistoryRecordDB)
            .filter(HistoryRecordDB.telegram_id == user["id"])
            .order_by(HistoryRecordDB.date, HistoryRecordDB.time)
            .all()
        )

    records = await run_db(_get_history)
    return [
        HistoryRecordSchema(
            id=r.id,
            date=r.date,
            time=r.time,
            sugar=r.sugar,
            carbs=r.carbs,
            breadUnits=r.bread_units,
            insulin=r.insulin,
            notes=r.notes,
            type=_validate_history_type(r.type, status_code=500),
        )
        for r in records
    ]


@app.delete("/api/history/{record_id}")
async def delete_history(record_id: str, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    """Delete a history record after verifying ownership."""

    def _get_record(session: Session) -> HistoryRecordDB | None:
        return session.get(HistoryRecordDB, record_id)

    record = await run_db(_get_record)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    if record.telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")

    def _delete_record(session: Session) -> None:
        obj = session.get(HistoryRecordDB, record_id)
        if obj:
            session.delete(obj)
            if not commit(session):
                raise HTTPException(status_code=500, detail="db commit failed")

    try:
        await run_db(_delete_record)
    except SQLAlchemyError as exc:  # pragma: no cover - database errors
        logger.exception("database error while deleting record")
        raise HTTPException(status_code=500, detail="database error") from exc
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover - convenience for manual execution
    import uvicorn

    uvicorn.run("services.api.app.main:app", host="0.0.0.0", port=8000)
