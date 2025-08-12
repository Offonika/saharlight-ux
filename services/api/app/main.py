import logging
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .middleware.auth import AuthMiddleware
from .schemas.timezone import TimezoneSchema
from .services.profile import set_timezone
from .services import init_db
from .config import UVICORN_WORKERS
from . import legacy

logger = logging.getLogger(__name__)

app = FastAPI()
app.router.redirect_slashes = True
app.add_middleware(AuthMiddleware)
app.include_router(legacy.router)

BASE_DIR = Path(__file__).resolve().parent.parent / "webapp"
UI_DIR = (BASE_DIR / "ui" / "dist").resolve()
PUBLIC_DIR = (BASE_DIR / "public").resolve()


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}


@app.post("/timezone")
async def api_timezone(data: TimezoneSchema) -> dict:
    try:
        ZoneInfo(data.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone") from exc
    await set_timezone(data.telegram_id, data.tz)
    return {"status": "ok"}


# ---------- UI serving ----------

def serve_index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html", headers={"Cache-Control": "no-store"})


if UI_DIR.exists():
    app.mount("/ui/assets", StaticFiles(directory=UI_DIR / "assets"), name="ui-assets")


@app.get("/ui", include_in_schema=False)
@app.head("/ui", include_in_schema=False)
async def ui_root() -> FileResponse:
    return serve_index()


@app.get("/ui/", include_in_schema=False)
@app.head("/ui/", include_in_schema=False)
async def ui_root_slash() -> FileResponse:
    return serve_index()


@app.get("/ui/{full_path:path}", include_in_schema=False)
async def ui_files(full_path: str) -> FileResponse:
    target = UI_DIR / full_path
    if target.exists():
        return FileResponse(target)
    return serve_index()


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui")


app.mount("/", StaticFiles(directory=str(PUBLIC_DIR)), name="public-root")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    init_db()
    uvicorn.run(
        "services.api.app.main:app", host="0.0.0.0", port=8000, workers=UVICORN_WORKERS
    )
