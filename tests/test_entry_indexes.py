from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_entry_indexes_usage() -> None:
    SessionLocal = setup_db()

    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.flush()
        session.add(db.Entry(telegram_id=1, event_time=datetime.utcnow()))
        session.commit()

        plan_tg = session.execute(
            sa.text("EXPLAIN QUERY PLAN SELECT * FROM entries WHERE telegram_id=1")
        ).all()
        assert any("USING INDEX ix_entries_telegram_id" in row[3] for row in plan_tg)

        plan_time = session.execute(
            sa.text(
                "EXPLAIN QUERY PLAN SELECT * FROM entries WHERE event_time >= '2000-01-01'"
            )
        ).all()
        assert any("USING INDEX ix_entries_event_time" in row[3] for row in plan_time)
