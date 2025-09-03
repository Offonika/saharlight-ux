from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import time as dt_time
import logging
from pathlib import Path
import sys
from typing import cast
import zoneinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ────────── Path-хаки, когда файл запускают напрямую ──────────
if __name__ == "__main__" and __package__ is None:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "services.api.app"

# ────────── std / 3-rd party ──────────
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import AliasChoices, BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# ────────── local ──────────
from . import config, reminder_events
from .diabetes.services.db import (
    HistoryRecord as HistoryRecordDB,
    Timezone as TimezoneDB,
    User as UserDB,
    init_db,
    run_db,
)
from .diabetes.services.repository import CommitError, commit
from .legacy import router as legacy_router
from .routers.internal_reminders import router as internal_reminders_router
from .routers.stats import router as stats_router
from .routers import metrics
from .routers.billing import router as billing_router
from .schemas.history import ALLOWED_HISTORY_TYPES, HistoryRecordSchema, HistoryType
from .schemas.role import RoleSchema
from .services.profile import patch_user_settings
from .diabetes.schemas.profile import ProfileSettingsIn, ProfileSettingsOut
from .schemas.user import UserContext
from .services.user_roles import get_user_role, set_user_role
from .telegram_auth import require_tg_user
from services.api.app.diabetes.services.gpt_client import dispose_openai_clients
from services.api.app.diabetes.utils.openai_utils import dispose_http_client
from .diabetes.handlers.reminder_jobs import DefaultJobQueue

# ────────── init ──────────
logger = logging.getLogger(__name__)
settings = config.get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        init_db()  # создаёт/инициализирует БД
    except (ValueError, SQLAlchemyError) as exc:
        logger.error("Failed to initialize the database: %s", exc)
        raise RuntimeError(
            "Database initialization failed. Please check your configuration and try again."
        ) from exc
    jq = cast(DefaultJobQueue | None, getattr(app.state, "job_queue", None))
    reminder_events.register_job_queue(jq)
    try:
        yield
    finally:
        reminder_events.register_job_queue(None)
        await dispose_http_client()
        await dispose_openai_clients()


app = FastAPI(title="Diabetes Assistant API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_origin] if settings.public_origin else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValidationError)
async def pydantic_422(_: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ────────── роуты статистики / legacy ──────────
# ────────── роутер с префиксом /api ──────────
api_router = APIRouter()
api_router.include_router(stats_router)
api_router.include_router(legacy_router)
api_router.include_router(metrics.router)
api_router.include_router(billing_router)

# ────────── статические файлы UI ──────────
BASE_DIR = Path(__file__).resolve().parents[2] / "webapp"
DIST_DIR = BASE_DIR / "ui" / "dist"
UI_DIR = DIST_DIR if (DIST_DIR / "index.html").exists() else BASE_DIR / "ui"
UI_DIR = UI_DIR.resolve()


def get_ui_base_url() -> str:
    """Return the UI base URL without a trailing slash."""

    return config.get_settings().ui_base_url.rstrip("/")


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


# ────────── timezones list ──────────
@api_router.get("/timezones")
async def get_timezones() -> list[str]:
    return sorted(zoneinfo.available_timezones())


# ────────── timezone ──────────
@api_router.get("/timezone")
async def get_timezone(_: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    def _get_timezone(session: Session) -> TimezoneDB | None:
        return session.get(TimezoneDB, 1)

    tz_row = await run_db(_get_timezone)
    if not tz_row:
        raise HTTPException(status_code=404, detail="timezone not set")
    try:
        ZoneInfo(tz_row.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone entry") from exc
    return {"tz": tz_row.tz}


@api_router.put("/timezone")
async def put_timezone(
    data: Timezone, _: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
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
        try:
            commit(session)
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save_timezone)
    return {"status": "ok"}


# ────────── profile/self ──────────
@api_router.get("/profile/self")
async def profile_self(user: UserContext = Depends(require_tg_user)) -> UserContext:
    return user


@api_router.patch("/profile", response_model=ProfileSettingsOut)
async def profile_patch(
    data: ProfileSettingsIn,
    device_tz: str | None = Query(None, alias="deviceTz"),
    user: UserContext = Depends(require_tg_user),
) -> ProfileSettingsOut:
    return await patch_user_settings(user["id"], data, device_tz)


# ────────── static UI files ──────────
@app.get(f"{get_ui_base_url()}/{{full_path:path}}", include_in_schema=False)
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


@app.get(get_ui_base_url() or "/", include_in_schema=False)
async def catch_root_ui() -> FileResponse:
    return await catch_all_ui("")


# ────────── user CRUD / roles ──────────
@api_router.post("/user")
async def create_user(
    data: WebUser, user: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
    if data.telegramId != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")

    def _create_user(session: Session) -> None:
        db_user = session.get(UserDB, data.telegramId)
        if db_user is None:
            session.add(UserDB(telegram_id=data.telegramId, thread_id="webapp"))
        try:
            commit(session)
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_create_user)
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

    def _save(session: Session) -> None:
        obj = session.get(HistoryRecordDB, data.id)
        if obj and obj.telegram_id != user["id"]:
            raise HTTPException(status_code=403, detail="forbidden")
        if obj is None:
            obj = HistoryRecordDB(id=data.id, telegram_id=user["id"])
            session.add(obj)
        obj.date = data.date
        obj.time = dt_time.fromisoformat(data.time)
        obj.sugar = data.sugar
        obj.carbs = data.carbs
        obj.bread_units = data.breadUnits
        obj.insulin = data.insulin
        obj.notes = data.notes
        obj.type = validated_type
        try:
            commit(session)
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save)
    return {"status": "ok"}


@api_router.get("/history", operation_id="historyGet", tags=["History"])
async def get_history(
    limit: int | None = Query(None, ge=1),
    user: UserContext = Depends(require_tg_user),
) -> list[HistoryRecordSchema]:
    def _query(session: Session) -> list[HistoryRecordDB]:
        query = (
            session.query(HistoryRecordDB)
            .filter(HistoryRecordDB.telegram_id == user["id"])
            .order_by(HistoryRecordDB.date.desc(), HistoryRecordDB.time.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    records = await run_db(_query)

    result: list[HistoryRecordSchema] = []
    for r in records:
        if r.type in ALLOWED_HISTORY_TYPES:
            result.append(
                HistoryRecordSchema(
                    id=r.id,
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
    def _get(session: Session) -> HistoryRecordDB | None:
        return session.get(HistoryRecordDB, id)

    record = await run_db(_get)
    if record is None:
        raise HTTPException(status_code=404, detail="not found")
    if record.telegram_id != user["id"]:
        raise HTTPException(status_code=403, detail="forbidden")

    def _delete(session: Session) -> None:
        session.delete(record)
        try:
            commit(session)
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_delete)
    return {"status": "ok"}


# ────────── include router ──────────
app.include_router(internal_reminders_router)
app.include_router(api_router, prefix="/api")

# ────────── run (for local testing) ──────────
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("services.api.app.main:app", host="0.0.0.0", port=8000, ws="wsproto")
