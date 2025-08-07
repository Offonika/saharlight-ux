"""Minimal FastAPI application serving the timezone detector page."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()
BASE_DIR = Path(__file__).parent


@app.get("/")
async def index() -> FileResponse:  # pragma: no cover - trivial
    """Return the main page."""
    return FileResponse(BASE_DIR / "index.html")


if __name__ == "__main__":  # pragma: no cover - manual start
    import uvicorn

    workers = int(os.getenv("UVICORN_WORKERS", "1"))
    uvicorn.run(
        "webapp.server:app",
        host="0.0.0.0",
        port=8000,
        workers=workers,
    )
