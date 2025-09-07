from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys
from typing import cast

# ────────── Path-хаки, когда файл запускают напрямую ──────────
if __name__ == "__main__" and __package__ is None:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    __package__ = "services.api.app"

# ────────── std / 3-rd party ──────────
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

# ────────── local ──────────
from . import config, reminder_events
from services.api.app.assistant.repositories.logs import (
    start_flush_task,
    stop_flush_task,
)
from .diabetes.handlers.reminder_jobs import DefaultJobQueue
from .diabetes.services.db import init_db, run_db  # noqa: F401
from services.api.app.diabetes.services.gpt_client import dispose_openai_clients
from services.api.app.diabetes.utils.openai_utils import dispose_http_client
from .telegram_auth import require_tg_user  # noqa: F401
from .legacy import router as legacy_router
from .routers import metrics
from .routers.billing import router as billing_router
from .routers.health import router as health_router
from .routers.history import router as history_router
from .routers.internal_reminders import router as internal_reminders_router
from .routers.onboarding import router as onboarding_router
from .routers.profile import router as profile_router
from .routers.stats import router as stats_router
from .routers.timezones import router as timezones_router
from .routers.users import router as users_router
from .routers.webapp import router as webapp_router

# ────────── init ──────────
logger = logging.getLogger(__name__)
settings = config.get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        init_db()  # создаёт/инициализирует БД
    except (ValueError, SQLAlchemyError) as exc:
        logger.error("Failed to initialize the database: %s", exc)
        raise RuntimeError("Database initialization failed. Please check your configuration and try again.") from exc
    jq = cast(DefaultJobQueue | None, getattr(app.state, "job_queue", None))
    reminder_events.register_job_queue(jq)
    if settings.learning_logging_required:
        start_flush_task()
    try:
        yield
    finally:
        reminder_events.register_job_queue(None)
        await dispose_http_client()
        await dispose_openai_clients()
        await stop_flush_task()


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
api_router.include_router(profile_router)
api_router.include_router(timezones_router)
api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(history_router)

# ────────── include router ──────────
app.include_router(internal_reminders_router)
app.include_router(metrics.router)
app.include_router(onboarding_router)
app.include_router(api_router, prefix="/api")
app.include_router(webapp_router)

# ────────── run (for local testing) ──────────
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("services.api.app.main:app", host="0.0.0.0", port=8000, ws="wsproto")
