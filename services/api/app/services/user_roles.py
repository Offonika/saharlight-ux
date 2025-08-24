from __future__ import annotations

from typing import cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..diabetes.services.db import SessionLocal, UserRole, run_db
from ..diabetes.services.repository import CommitError, commit
from ..types import SessionProtocol

ALLOWED_ROLES = {"patient", "clinician", "org_admin", "superadmin"}


async def get_user_role(user_id: int) -> str | None:
    def _get(session: SessionProtocol) -> str | None:
        obj = cast(UserRole | None, session.get(UserRole, user_id))
        return obj.role if obj else None

    return await run_db(_get, sessionmaker=SessionLocal)


async def set_user_role(user_id: int, role: str) -> None:
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="invalid role")

    def _save(session: SessionProtocol) -> None:
        obj = cast(UserRole | None, session.get(UserRole, user_id))
        if obj is None:
            obj = UserRole(user_id=user_id, role=role)
            cast(Session, session).add(obj)
        else:
            obj.role = role
        try:
            commit(cast(Session, session))
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save, sessionmaker=SessionLocal)
