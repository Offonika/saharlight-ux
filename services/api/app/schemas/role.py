from __future__ import annotations

from pydantic import BaseModel


class RoleSchema(BaseModel):
    role: str
