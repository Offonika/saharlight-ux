from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, Integer, TIMESTAMP, Enum as SAEnum, JSON, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from ..diabetes.services import repository
from ..diabetes.services.db import Base

logger = logging.getLogger(__name__)


class BillingEvent(str, Enum):
    """Enumerated billing events."""

    INIT = "init"
    CHECKOUT_CREATED = "checkout_created"
    WEBHOOK_OK = "webhook_ok"
    EXPIRED = "expired"
    CANCELED = "canceled"


class BillingLog(Base):
    """Database model for billing events."""

    __tablename__ = "billing_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    event: Mapped[BillingEvent] = mapped_column(SAEnum(BillingEvent, name="billing_event"), nullable=False)
    ts: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON)


__all__ = ["BillingLog", "BillingEvent", "log_billing_event"]


def log_billing_event(
    session: Session,
    user_id: int,
    event: BillingEvent,
    context: dict[str, Any] | None = None,
) -> None:
    """Persist a billing event."""

    log = BillingLog(user_id=user_id, event=event, context=context)
    session.add(log)
    try:
        repository.commit(session)
    except repository.CommitError:  # pragma: no cover - logging only
        logger.exception("Failed to persist billing event %s for user %s", event.value, user_id)
        raise
