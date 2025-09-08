"""User management endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AliasChoices, BaseModel, Field

from ..diabetes.services import db as db_module
from ..diabetes.services.users import ensure_user_exists
from ..schemas.role import RoleSchema
from ..schemas.user import UserContext
from ..services.user_roles import get_user_role, set_user_role
from ..telegram_auth import require_tg_user


logger = logging.getLogger(__name__)

router = APIRouter()


class WebUser(BaseModel):
    telegramId: int = Field(
        alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id")
    )


@router.post("/user")
async def create_user(
    data: WebUser, user: UserContext = Depends(require_tg_user)
) -> dict[str, str]:
    """Create a user record if it does not exist."""

    if data.telegramId != user["id"]:
        raise HTTPException(status_code=403, detail="telegram id mismatch")

    await ensure_user_exists(
        data.telegramId, thread_id="webapp", session_factory=db_module.SessionLocal
    )
    logger.info("Ensured user %s via API", data.telegramId)
    return {"status": "ok"}


@router.get("/user/{user_id}/role")
async def get_role(user_id: int) -> RoleSchema:
    """Return user role."""

    role = await get_user_role(user_id)
    return RoleSchema(role=role or "patient")


@router.put("/user/{user_id}/role")
async def put_role(user_id: int, data: RoleSchema) -> RoleSchema:
    """Set user role."""

    await set_user_role(user_id, data.role)
    return RoleSchema(role=data.role)

