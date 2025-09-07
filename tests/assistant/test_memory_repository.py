from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories.memory import get_memory, upsert_memory
from services.api.app.diabetes.services import db


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record) -> None:  # pragma: no cover - setup
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_get_memory_missing() -> None:
    SessionLocal = setup_db()
    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()
        assert get_memory(session, 1) is None


def test_upsert_and_get_memory() -> None:
    SessionLocal = setup_db()
    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()

        now = datetime.now(tz=timezone.utc)
        mem = upsert_memory(
            session,
            user_id=1,
            summary_text="hello",
            turn_count=1,
            last_turn_at=now,
        )
        assert mem.summary_text == "hello"
        fetched = get_memory(session, 1)
        assert fetched is not None
        assert fetched.summary_text == "hello"

        later = now + timedelta(minutes=1)
        upsert_memory(
            session,
            user_id=1,
            summary_text="bye",
            turn_count=2,
            last_turn_at=later,
        )
        fetched2 = get_memory(session, 1)
        assert fetched2 is not None
        assert fetched2.summary_text == "bye"
        assert fetched2.turn_count == 2
