from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CommandSchema(BaseModel):
    """Schema for GPT parsed command."""

    action: str
    entry_date: Optional[str] = None
    time: Optional[str] = None
    fields: Optional[dict[str, object]] = None
