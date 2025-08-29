from datetime import date, time
from typing import Any

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
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


def test_history_record_requires_existing_user() -> None:
    SessionLocal = setup_db()

    with SessionLocal() as session:
        session.add(
            db.HistoryRecord(
                id="1",
                telegram_id=999,
                date=date.today(),
                time=time(12, 0),
                type="note",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
