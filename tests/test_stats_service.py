from typing import ContextManager, Generator, cast
import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import Base, HistoryRecord, SessionMaker
from services.api.app.services import stats


@pytest.fixture()
def session_factory() -> Generator[SessionMaker[SASession], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession: SessionMaker[SASession] = sessionmaker(
        bind=engine, class_=SASession, autoflush=False, autocommit=False
    )
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_get_day_stats(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    today = datetime.date.today()
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(
            HistoryRecord(
                id="1",
                telegram_id=1,
                date=today,
                time=datetime.time(8, 0),
                sugar=5.0,
                bread_units=1.0,
                insulin=2.0,
                type="sugar",
            )
        )
        session.add(
            HistoryRecord(
                id="2",
                telegram_id=1,
                date=today,
                time=datetime.time(12, 0),
                sugar=7.0,
                bread_units=2.0,
                insulin=3.0,
                type="sugar",
            )
        )
        session.commit()

    monkeypatch.setattr(stats, "SessionLocal", session_factory)

    result = await stats.get_day_stats(1)
    assert result is not None
    assert result.sugar == pytest.approx(6.0)
    assert result.breadUnits == pytest.approx(3.0)
    assert result.insulin == pytest.approx(5.0)
