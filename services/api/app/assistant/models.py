from __future__ import annotations

import sqlalchemy as sa
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.diabetes.services.db import Base


class Plan(Base):
    __tablename__ = "assistant_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


sa.Index(
    "uq_assistant_plans_user_active",
    Plan.user_id,
    unique=True,
    sqlite_where=Plan.active,
    postgresql_where=Plan.active,
)
