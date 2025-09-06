"""History CRUD endpoints."""

from __future__ import annotations

import logging
from datetime import time as dt_time
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query
import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..diabetes.services.db import HistoryRecord as HistoryRecordDB, run_db
from ..diabetes.services.repository import CommitError, commit
from ..schemas.history import (
    ALLOWED_HISTORY_TYPES,
    HistoryRecordSchema,
    HistoryType,
)
from ..schemas.user import UserContext
from ..telegram_auth import require_tg_user


logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_history_type(value: str, status_code: int = 400) -> HistoryType:
    if value not in ALLOWED_HISTORY_TYPES:
        raise HTTPException(status_code=status_code, detail="invalid history type")
    return cast(HistoryType, value)


@router.post("/history", operation_id="historyPost", tags=["History"])
async def post_history(data: HistoryRecordSchema, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    """Create or update a history record."""

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
        except CommitError:  # pragma: no cover - db error
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save)
    return {"status": "ok"}


@router.get("/history", operation_id="historyGet", tags=["History"])
async def get_history(
    limit: int | None = Query(None, ge=1),
    user: UserContext = Depends(require_tg_user),
) -> list[HistoryRecordSchema]:
    """Return list of history records."""

    def _query(session: Session) -> list[HistoryRecordDB]:
        stmt = (
            sa.select(HistoryRecordDB)
            .where(HistoryRecordDB.telegram_id == user["id"])
            .order_by(HistoryRecordDB.date.desc(), HistoryRecordDB.time.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return session.scalars(stmt).all()

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


@router.delete("/history/{id}", operation_id="historyIdDelete", tags=["History"])
async def delete_history(id: str, user: UserContext = Depends(require_tg_user)) -> dict[str, str]:
    """Delete history record by id."""

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
        except CommitError:  # pragma: no cover - db error
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_delete)
    return {"status": "ok"}
