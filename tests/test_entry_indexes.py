from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from services.api.app.diabetes.services.db import Base, dispose_engine


def _setup_engine() -> Engine:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_entry_uses_indexes() -> None:
    engine = _setup_engine()
    try:
        with engine.connect() as conn:
            plan = conn.execute(
                text("EXPLAIN QUERY PLAN SELECT * FROM entries WHERE telegram_id=1")
            ).fetchall()
        assert any(
            "USING INDEX" in row[-1] and "ix_entries_telegram_id" in row[-1]
            for row in plan
        )

        with engine.connect() as conn:
            plan = conn.execute(
                text(
                    "EXPLAIN QUERY PLAN SELECT * FROM entries WHERE event_time='2024-01-01 00:00:00'"
                )
            ).fetchall()
        assert any(
            "USING INDEX" in row[-1] and "ix_entries_event_time" in row[-1]
            for row in plan
        )
    finally:
        dispose_engine(engine)
