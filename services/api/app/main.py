from __future__ import annotations

from datetime import time as dt_time
import logging
import os
from pathlib import Path
import sys
from typing import Callable, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ────────── Path-хаки, когда файл запускают напрямую ──────────
if __name__ == "__main__" and __package__ is None:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "services.api.app"

# ────────── std / 3-rd party ──────────
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# ────────── local ──────────
from services.api.app.types import SessionProtocol
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
from services.api.app.diabetes.utils.openai_utils import dispose_http_client

# ────────── init ──────────
logger = logging.getLogger(__name__)
try:
    init_db()  # создаёт/инициализирует БД
except (ValueError, SQLAlchemyError) as exc:
    logger.error("Failed to initialize the database: %s", exc)
    raise RuntimeError(
        "Database initialization failed. Please check your configuration and try again."
    ) from exc

app = FastAPI(title="Diabetes Assistant API", version="1.0.0")


@app.on_event("shutdown")
async def shutdown_openai_client() -> None:
    dispose_http_client()


# ────────── роуты статистики / legacy ──────────
# ────────── роутер с префиксом /api ──────────
api_router = APIRouter()
api_router.include_router(stats_router)
api_router.include_router(legacy_router)

# ────────── статические файлы UI ──────────
BASE_DIR = Path(__file__).resolve().parents[2] / "webapp"
UI_DIR = (
    (BASE_DIR / "ui" / "dist")
    if (BASE_DIR / "ui" / "dist").exists()
    else (BASE_DIR / "ui")
)
UI_DIR = UI_DIR.resolve()
UI_BASE_URL = os.getenv("VITE_BASE_URL", "/ui/").rstrip("/")


# ────────── Schemas ──────────
class Timezone(BaseModel):
    tz: str


class WebUser(BaseModel):
    telegramId: int = Field(
        alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id")
    )


# ────────── helpers ──────────
def _validate_history_type(value: str, status_code: int = 400) -> HistoryType:
    if value not in ALLOWED_HISTORY_TYPES:
        raise HTTPException(status_code=status_code, detail="invalid history type")
    return cast(HistoryType, value)


# ────────── health & misc ──────────
@api_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ────────── timezone ──────────
@api_router.get("/timezone")
async def get_timezone(_: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    def _get_timezone(session: SessionProtocol) -> TimezoneDB | None:
        return cast(TimezoneDB | None, session.get(TimezoneDB, 1))

    tz_row = await run_db(
        cast(Callable[[Session], TimezoneDB | None], _get_timezone)
    )
    if not tz_row:
        raise HTTPException(status_code=404, detail="timezone not set")
    try:
        ZoneInfo(tz_row.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=500, detail="invalid timezone entry") from exc
    return {"tz": tz_row.tz}


@api_router.put("/timezone")
async def put_timezone(
    data: Timezone, _: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
    try:
        ZoneInfo(data.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone") from exc

    def _save_timezone(session: SessionProtocol) -> None:
        obj = cast(TimezoneDB | None, session.get(TimezoneDB, 1))
        if obj is None:
            obj = TimezoneDB(id=1, tz=data.tz)
            cast(Session, session).add(obj)
        else:
            obj.tz = data.tz
        if not commit(cast(Session, session)):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(cast(Callable[[Session], None], _save_timezone))
    return {"status": "ok"}


# ────────── profile/self ──────────
@api_router.get("/profile/self")
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
        if requested_file.suffix == ".js":
            return FileResponse(requested_file, media_type="text/javascript")
        return FileResponse(requested_file)
    return FileResponse(UI_DIR / "index.html")


@app.get(UI_BASE_URL or "/", include_in_schema=False)
async def catch_root_ui() -> FileResponse:
    return await catch_all_ui("")


# ────────── user CRUD / roles ──────────
@api_router.post("/user")
async def create_user(
    data: WebUser, user: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
    if data.telegramId != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")

    def _create_user(session: SessionProtocol) -> None:
        db_user = cast(UserDB | None, session.get(UserDB, data.telegramId))
        if db_user is None:
            cast(Session, session).add(
                UserDB(telegram_id=data.telegramId, thread_id="webapp")
            )
        if not commit(cast(Session, session)):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(cast(Callable[[Session], None], _create_user))
    return {"status": "ok"}


@api_router.get("/user/{user_id}/role")
async def get_role(user_id: int) -> RoleSchema:
    role = await get_user_role(user_id)
    return RoleSchema(role=role or "patient")


@api_router.put("/user/{user_id}/role")
async def put_role(user_id: int, data: RoleSchema) -> RoleSchema:
    await set_user_role(user_id, data.role)
    return RoleSchema(role=data.role)


# ────────── history (CRUD) ──────────
@api_router.post("/history", operation_id="historyPost", tags=["History"])
async def post_history(
    data: HistoryRecordSchema, user: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
    validated_type = _validate_history_type(data.type)

    def _save(session: SessionProtocol) -> None:
        obj = cast(HistoryRecordDB | None, session.get(HistoryRecordDB, data.id))
        if obj and obj.telegram_id != user["id"]:
            raise HTTPException(status_code=403, detail="forbidden")
        if obj is None:
            obj = HistoryRecordDB(id=data.id, telegram_id=user["id"])
            cast(Session, session).add(obj)
        obj.date = data.date
        obj.time = dt_time.fromisoformat(data.time)
        obj.sugar = data.sugar
        obj.carbs = data.carbs
        obj.bread_units = data.breadUnits
        obj.insulin = data.insulin
        obj.notes = data.notes
        obj.type = validated_type
        if not commit(cast(Session, session)):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(cast(Callable[[Session], None], _save))
    return {"status": "ok"}


@api_router.get("/history", operation_id="historyGet", tags=["History"])
async def get_history(
    user: UserContext = Depends(require_tg_user),
) -> list[HistoryRecordSchema]:
    def _query(session: Session) -> list[HistoryRecordDB]:
        return (
            session.query(HistoryRecordDB)
            .filter(HistoryRecordDB.telegram_id == user["id"])
            .order_by(HistoryRecordDB.date, HistoryRecordDB.time)
            .all()
        )

    records = await run_db(cast(Callable[[Session], list[HistoryRecordDB]], _query))

    result: list[HistoryRecordSchema] = []
    for r in records:
        if r.type in ALLOWED_HISTORY_TYPES:
            result.append(
                HistoryRecordSchema(
                    id=cast(str, r.id),
                    date=r.date,
                    time=r.time.strftime("%H:%M"),
                    sugar=r.sugar,
                    carbs=r.carbs,
                    breadUnits=r.bread_units,
                    insulin=r.insulin,
                    notes=r.notes,
                    type=cast(HistoryType, r.type),
                )
            )
    return result


@api_router.delete("/history/{id}", operation_id="historyIdDelete", tags=["History"])
async def delete_history(
    id: str, user: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
    def _get(session: SessionProtocol) -> HistoryRecordDB | None:
        return cast(HistoryRecordDB | None, session.get(HistoryRecordDB, id))

    record = await run_db(cast(Callable[[Session], HistoryRecordDB | None], _get))
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    if record.telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")

    def _delete(session: Session) -> None:
        session.delete(record)
        if not commit(session):
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(cast(Callable[[Session], None], _delete))
    return {"status": "ok"}


# ────────── include router ──────────
app.include_router(api_router, prefix="/api")

# ────────── run (for local testing) ──────────
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("services.api.app.main:app", host="0.0.0.0", port=8000)
