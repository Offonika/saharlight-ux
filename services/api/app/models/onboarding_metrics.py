from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Integer, String, TIMESTAMP, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.diabetes.services.db import Base


class OnboardingMetricEvent(Base):
    """Raw onboarding step event for metrics."""

    __tablename__ = "onboarding_events_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant: Mapped[str] = mapped_column(String, nullable=False)
    step: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_onboarding_events_metrics_variant_step_created_at",
            "variant",
            "step",
            "created_at",
        ),
    )


class OnboardingMetricDaily(Base):
    """Aggregated onboarding metrics per day."""

    __tablename__ = "onboarding_metrics_daily"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    variant: Mapped[str] = mapped_column(String, primary_key=True)
    step: Mapped[str] = mapped_column(String, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index(
            "ix_onboarding_metrics_daily_date_variant_step",
            "date",
            "variant",
            "step",
        ),
    )


__all__ = ["OnboardingMetricEvent", "OnboardingMetricDaily"]
