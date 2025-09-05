"""Routes serving the web application static files."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import config


logger = logging.getLogger(__name__)

router = APIRouter()

# The web application lives in the top-level ``services/webapp`` directory.
# ``__file__`` resolves to ``services/api/app/routers/webapp.py`` and we need to
# go three levels up (to ``services``) before appending ``webapp``. Previously we
# used ``parents[2]`` which pointed to ``services/api`` and resulted in resolving
# the UI path to ``services/api/webapp``. That directory does not contain the
# built UI assets, so tests looking for ``index.html`` failed. Using
# ``parents[3]`` correctly points to ``services/webapp``.
BASE_DIR = Path(__file__).resolve().parents[3] / "webapp"
DIST_DIR = BASE_DIR / "ui" / "dist"
UI_DIR = DIST_DIR if (DIST_DIR / "index.html").exists() else BASE_DIR / "ui"
UI_DIR = UI_DIR.resolve()


def get_ui_base_url() -> str:
    """Return the UI base URL without a trailing slash."""

    return config.get_settings().ui_base_url.rstrip("/")


@router.get(f"{get_ui_base_url()}/{{full_path:path}}", include_in_schema=False)
async def catch_all_ui(full_path: str) -> FileResponse:
    """Serve UI static files."""

    requested_file = (UI_DIR / full_path).resolve()
    try:
        requested_file.relative_to(UI_DIR)
    except ValueError as exc:  # pragma: no cover - path traversal
        raise HTTPException(status_code=404) from exc
    if requested_file.is_file():
        if requested_file.suffix == ".js":
            return FileResponse(requested_file, media_type="text/javascript")
        return FileResponse(requested_file)
    return FileResponse(UI_DIR / "index.html")


@router.get(get_ui_base_url() or "/", include_in_schema=False)
async def catch_root_ui() -> FileResponse:
    """Serve root UI entry point."""

    return await catch_all_ui("")

