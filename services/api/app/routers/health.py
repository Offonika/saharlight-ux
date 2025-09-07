"""Health check endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import SessionLocal, run_db


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return service health status."""

    return {"status": "ok"}


@router.get("/health/ping")
async def ping() -> JSONResponse:
    """Quickly ping the database connection pool."""

    def _ping(session: Session) -> None:
        session.execute(sa.text("SELECT 1"))

    try:
        await run_db(_ping, sessionmaker=SessionLocal)
    except Exception:
        logger.exception("Database ping failed")
        return JSONResponse({"status": "down"}, status_code=503)

    return JSONResponse({"status": "up"})
