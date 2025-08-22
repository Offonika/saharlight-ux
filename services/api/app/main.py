from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ────────── Path-хаки, когда файл запускают напрямую ──────────
if __name__ == "__main__" and __package__ is None:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "services.api.app"

# ────────── std / 3-rd party ──────────
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# ────────── local ──────────
from .config import settings
from .diabetes.services.db import (
    HistoryRecord as HistoryRecordDB,
    Timezone as TimezoneDB,
    User as UserDB,
    init_db,
    run_db,
)
from .diabetes.services.repository import commit
from .legacy import router as legacy_router
from .routers.stats import router as stats_router
from .schemas.history import ALLOWED_HISTORY_TYPES, HistoryRecordSchema, HistoryType
from .schemas.role import RoleSchema
from .schemas.user import UserContext
from .services.user_roles import get_user_role, set_user_role
from .telegram_auth import require_tg_user

# ────────── init ──────────
logger = logging.getLogger(__name__)
init_db()  # создаёт/инициализирует БД

app = FastAPI(title="Diabetes Assistant API", version="1.0.0")

# ────────── profiles (front expects list) ──────────
@app.get("/api/profiles", operation_id="profilesGet", tags=["profiles"])
@app.get("/profiles", include_in_schema=False)  # legacy-путь
async def get_profiles(
    telegramId: int | None = Query(None),
    telegram_id: int | None = Query(None, alias="telegram_id"),
    user: UserContext = Depends(require_tg_user),
) -> list[UserContext]:
    """
    Telegram-Web-App ждёт массив профилей.
    Бэкенд однопользовательский → возвращаем список из одного текущего пользователя.
    Если query-параметр указан и не совпадает с auth-пользователем — 403.
    """
    tid = telegramId or telegram_id
    if tid is not None and tid != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")
    return [user]

# ────────── роуты статистики / legacy ──────────
app.include_router(stats_router,   prefix="/api")
app.include_router(legacy_router,  prefix="/api")

# ────────── статические файлы UI ──────────
BASE_DIR   = Path(__file__).resolve().parents[2] / "webapp"
UI_DIR     = (BASE_DIR / "ui" / "dist") if (BASE_DIR / "ui" / "dist").exists() else (BASE_DIR / "ui")
UI_DIR     = UI_DIR.resolve()
UI_BASE_URL = os.getenv("VITE_BASE_URL", "/ui/").rstrip("/")

# ────────── Schemas ──────────
class Timezone(BaseModel):
    tz: str

class WebUser(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))

# ────────── helpers ──────────
def _validate_history_type(value: str, status_code: int = 400) -> HistoryType:
    if value not in ALLOWED_HISTORY_TYPES:
        raise HTTPException(status_code=status_code, detail="invalid history type")
    return cast(HistoryType, value)

# ────────── health & misc ──────────
@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}

# ────────── timezone ──────────
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

    def _save_timezone(session: Session) -> None:
        obj = session.get(TimezoneDB, 1)
        if obj is None:
            obj = TimezoneDB(id=1, tz=data.tz)
            session.add(obj)
        else:
            obj.tz = data.tz
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save_timezone)
    return {"status": "ok"}

# ────────── profile/self ──────────
@app.get("/profile/self")
@app.get("/api/profile/self")
async def profile_self(user: UserContext = Depends(require_tg_user)) -> UserContext:
    return user

# ────────── static UI files ──────────
@app.get(f"{UI_BASE_URL}/{{full_path:path}}", include_in_schema=False)
async def catch_all_ui(full_path: str) -> FileResponse:
    requested_file = (UI_DIR / full_path).resolve()
    try:
        requested_file.relative_to(UI_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=404) from exc
    if requested_file.is_file():
        return FileResponse(requested_file)
    return FileResponse(UI_DIR / "index.html")

@app.get(UI_BASE_URL or "/", include_in_schema=False)
async def catch_root_ui() -> FileResponse:
    return await catch_all_ui("")

# ────────── user CRUD / roles ──────────
@app.post("/user")
async def create_user(data: WebUser, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    if data.telegramId != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")

    def _create_user(session: Session) -> None:
        db_user = session.get(UserDB, data.telegramId)
        if db_user is None:
            session.add(UserDB(telegram_id=data.telegramId, thread_id="webapp"))
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_create_user)
    return {"status": "ok"}

@app.get("/user/{user_id}/role")
async def get_role(user_id: int) -> RoleSchema:
    role = await get_user_role(user_id)
    return RoleSchema(role=role or "patient")

@app.put("/user/{user_id}/role")
async def put_role(user_id: int, data: RoleSchema) -> RoleSchema:
    await set_user_role(user_id, data.role)
    return RoleSchema(role=data.role)

# ────────── history (CRUD) ──────────
@app.post("/history")
@app.post("/api/history")
async def post_history(data: HistoryRecordSchema, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    validated_type = _validate_history_type(data.type)

    def _save(session: Session) -> None:
        obj = session.get(HistoryRecordDB, data.id)
        if obj and obj.telegram_id != user["id"]:
            raise HTTPException(status_code=403, detail="forbidden")
        if obj is None:
            obj = HistoryRecordDB(id=data.id, telegram_id=user["id"])
            session.add(obj)
        obj.date = data.date.isoformat()
        obj.time = data.time.strftime("%H:%M")
        obj.sugar = data.sugar
        obj.carbs = data.carbs
        obj.bread_units = data.breadUnits
        obj.insulin = data.insulin
        obj.notes = data.notes
        obj.type = validated_type
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save)
    return {"status": "ok"}

@app.get("/history")
@app.get("/api/history")
async def get_history(user: UserContext = Depends(require_tg_user)) -> list[HistoryRecordSchema]:
    def _query(session: Session) -> list[HistoryRecordDB]:
        return (
            session.query(HistoryRecordDB)
            .filter(HistoryRecordDB.telegram_id == user["id"])
            .order_by(HistoryRecordDB.date, HistoryRecordDB.time)
            .all()
        )

    records = await run_db(_query)
    result: list[HistoryRecordSchema] = []
    for r in records:
        if r.type in ALLOWED_HISTORY_TYPES:
            result.append(
                HistoryRecordSchema(
                    id=r.id,
                    date=r.date,
                    time=r.time,
                    sugar=r.sugar,
                    carbs=r.carbs,
                    breadUnits=r.bread_units,
                    insulin=r.insulin,
                    notes=r.notes,
                    type=cast(HistoryType, r.type),
                )
            )
    return result

@app.delete("/history/{record_id}")
@app.delete("/api/history/{record_id}")
async def delete_history(record_id: str, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    def _get(session: Session) -> HistoryRecordDB | None:
        return session.get(HistoryRecordDB, record_id)

    record = await run_db(_get)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    if record.telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")

    def _delete(session: Session) -> None:
        session.delete(record)
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_delete)
    return {"status": "ok"}

# ────────── run (for local testing) ──────────
if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    uvicorn.run("services.api.app.main:app", host="0.0.0.0", port=8000)
