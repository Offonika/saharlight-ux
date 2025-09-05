"""Timezone related endpoints."""

from __future__ import annotations

import logging
import zoneinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..diabetes.services.db import Timezone as TimezoneDB, run_db
from ..diabetes.services.repository import CommitError, commit
from ..schemas.user import UserContext
from ..telegram_auth import require_tg_user


logger = logging.getLogger(__name__)

router = APIRouter()


class Timezone(BaseModel):
    tz: str


@router.get("/timezones")
async def get_timezones() -> list[str]:
    """Return sorted list of all available timezones."""

    return sorted(zoneinfo.available_timezones())


@router.get("/timezone")
async def get_timezone(_: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    """Return stored timezone value."""

    def _get_timezone(session: Session) -> TimezoneDB | None:
        return session.get(TimezoneDB, 1)

    tz_row = await run_db(_get_timezone)
    if not tz_row:
        raise HTTPException(status_code=404, detail="timezone not set")
    try:
        ZoneInfo(tz_row.tz)
    except ZoneInfoNotFoundError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="invalid timezone entry") from exc
    return {"tz": tz_row.tz}


@router.put("/timezone")
async def put_timezone(
    data: Timezone, _: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
    """Store provided timezone."""

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
        except CommitError:  # pragma: no cover - db error
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save_timezone)
    return {"status": "ok"}

