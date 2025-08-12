import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .schemas import ProfileSchema, ReminderSchema, TimezoneSchema
from .services import list_reminders, save_profile, save_reminder, set_timezone, init_db

logger = logging.getLogger(__name__)

app = FastAPI()
app.router.redirect_slashes = True

BASE_DIR = Path(__file__).resolve().parent.parent / "webapp"
UI_DIR = (BASE_DIR / "ui" / "dist").resolve()
PUBLIC_DIR = (BASE_DIR / "public").resolve()


@app.post("/api/timezone")
async def api_timezone(data: TimezoneSchema) -> dict:
    try:
        ZoneInfo(data.tz)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=400, detail="invalid timezone") from exc
    await set_timezone(data.telegram_id, data.tz)
    return {"status": "ok"}


@app.post("/api/profile")
async def api_profile(data: ProfileSchema) -> dict:
    await save_profile(data)
    return {"status": "ok"}


@app.get("/api/reminders")
async def api_reminders(telegram_id: int, id: int | None = None):
    rems = await list_reminders(telegram_id)
    if id is None:
        return [
            {
                "id": r.id,
                "type": r.type,
                "title": r.type,
                "time": r.time,
                "active": r.is_enabled,
                "interval": r.interval_hours,
            }
            for r in rems
        ]
    for r in rems:
        if r.id == id:
            return {
                "id": r.id,
                "type": r.type,
                "title": r.type,
                "time": r.time,
                "active": r.is_enabled,
                "interval": r.interval_hours,
            }
    return {}


@app.post("/api/reminders")
async def api_reminders_post(data: ReminderSchema) -> dict:
    rid = await save_reminder(data)
    return {"status": "ok", "id": rid}


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

    workers = int(os.getenv("UVICORN_WORKERS", "1"))
    init_db()
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, workers=workers)
