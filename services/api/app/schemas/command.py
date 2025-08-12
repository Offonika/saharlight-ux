from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class CommandSchema(BaseModel):
    """Schema for GPT parsed command."""

    action: str
    entry_date: Optional[str] = None
    time: Optional[str] = None
    fields: dict[str, Any]
