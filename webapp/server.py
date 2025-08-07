"""Minimal FastAPI application serving the timezone detector page."""
from __future__ import annotations

import os
from json import JSONDecodeError
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

app = FastAPI()
BASE_DIR = Path(__file__).parent
REMINDERS: dict[int, dict] = {}
NEXT_ID = 1


class ProfileSchema(BaseModel):
    """Schema for profile data."""

    icr: float
    cf: float
    target: float
    low: float
    high: float


class ReminderSchema(BaseModel):
    """Schema for reminder data."""

    id: int | None = None
    rem_type: str | None = None
    value: str | None = None
    text: str | None = None


@app.get("/")
async def index() -> FileResponse:  # pragma: no cover - trivial
    """Return the main page."""
    return FileResponse(BASE_DIR / "index.html")


@app.get("/profile")
async def profile() -> FileResponse:  # pragma: no cover - trivial
    """Return the profile form page."""
    return FileResponse(BASE_DIR / "profile.html")


@app.post("/profile")
async def profile_post(request: Request) -> dict:  # pragma: no cover - simple
    """Accept submitted profile data."""
    try:
        data = await request.json()
    except JSONDecodeError as exc:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="invalid JSON format") from exc
    try:
        ProfileSchema(**data)
    except ValidationError as exc:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="invalid data") from exc
    return {"status": "ok"}


@app.get("/reminder")
async def reminder_form() -> FileResponse:  # pragma: no cover - trivial
    """Return the reminder form page."""
    return FileResponse(BASE_DIR / "reminder.html")


@app.get("/reminders")
async def reminders_get(id: int | None = None) -> dict | list[dict]:  # pragma: no cover - simple
    """Return stored reminders (in-memory demo store)."""
    if id is None:
        return list(REMINDERS.values())
    return REMINDERS.get(id, {})


@app.post("/reminders")
async def reminders_post(request: Request) -> dict:  # pragma: no cover - simple
    """Save reminder data to demo store."""
    global NEXT_ID
    try:
        data = await request.json()
    except JSONDecodeError as exc:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="invalid JSON format") from exc
    try:
        reminder = ReminderSchema(**data)
    except ValidationError as exc:  # pragma: no cover - validation
        raise HTTPException(status_code=400, detail="invalid data") from exc
    raw_id = reminder.id if reminder.id is not None else NEXT_ID
    rid = raw_id
    if rid < 0:
        raise HTTPException(status_code=400, detail="id must be non-negative")
    NEXT_ID = max(NEXT_ID, rid + 1)
    REMINDERS[rid] = {**reminder.dict(exclude_none=True), "id": rid}
    return {"status": "ok", "id": rid}


if __name__ == "__main__":  # pragma: no cover - manual start
    import uvicorn

    workers = int(os.getenv("UVICORN_WORKERS", "1"))
    uvicorn.run(
        "webapp.server:app",
        host="0.0.0.0",
        port=8000,
        workers=workers,
    )
