"""Health check endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return service health status."""

    return {"status": "ok"}

