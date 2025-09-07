from __future__ import annotations

import logging
from datetime import datetime
from typing import cast

import sqlalchemy as sa
from sqlalchemy import BigInteger, Integer, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from ...diabetes.services.db import Base, SessionLocal, run_db
from ...diabetes.services.repository import commit
from ...types import SessionProtocol

logger = logging.getLogger(__name__)


class Progress(Base):
    """Store learning progress for a user and a lesson."""

    __tablename__ = "assistant_progress"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lesson: Mapped[str] = mapped_column(String, primary_key=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = ["Progress", "get_progress", "upsert_progress"]


async def get_progress(user_id: int, lesson: str) -> Progress | None:
    """Return stored progress for ``user_id`` and ``lesson`` if any."""

    def _get(session: SessionProtocol) -> Progress | None:
        stmt = sa.select(Progress).where(
            Progress.user_id == user_id, Progress.lesson == lesson
        )
        result = session.execute(stmt).scalar_one_or_none()
        return cast(Progress | None, result)

    return await run_db(_get, sessionmaker=SessionLocal)


async def upsert_progress(user_id: int, lesson: str, step: int) -> None:
    """Insert or update progress ensuring idempotency."""

    def _upsert(session: SessionProtocol) -> None:
        stmt = insert(Progress).values(user_id=user_id, lesson=lesson, step=step)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Progress.user_id, Progress.lesson],
                set_={
                    "step": sa.func.max(Progress.step, stmt.excluded.step),
                    "updated_at": func.now(),
                },
            )
        )
        commit(cast(Session, session))

    await run_db(_upsert, sessionmaker=SessionLocal)
