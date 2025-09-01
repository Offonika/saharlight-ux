from __future__ import annotations

from datetime import time

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, User


class UserSettings(Base):
    """Per-user configurable settings."""

    __tablename__ = "user_settings"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), primary_key=True
    )
    icr: Mapped[float] = mapped_column(Float, default=1.0)
    cf: Mapped[float] = mapped_column(Float, default=1.0)
    target_bg: Mapped[float] = mapped_column(Float, default=5.5)
    low_threshold: Mapped[float] = mapped_column(Float, default=4.0)
    high_threshold: Mapped[float] = mapped_column(Float, default=8.0)
    quiet_start: Mapped[time] = mapped_column(Time, default=time(23, 0))
    quiet_end: Mapped[time] = mapped_column(Time, default=time(7, 0))
    sos_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship("User")
