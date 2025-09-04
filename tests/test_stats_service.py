from typing import ContextManager, Generator, cast
import datetime
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import Base, Entry, SessionMaker
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
            Entry(
                telegram_id=1,
                event_time=datetime.datetime.combine(
                    today, datetime.time(8, 0), tzinfo=datetime.timezone.utc
                ),
                sugar_before=5.0,
                xe=1.0,
                dose=2.0,
            )
        )
        session.add(
            Entry(
                telegram_id=1,
                event_time=datetime.datetime.combine(
                    today, datetime.time(12, 0), tzinfo=datetime.timezone.utc
                ),
                sugar_before=7.0,
                xe=2.0,
                dose=3.0,
            )
        )
        session.commit()

    monkeypatch.setattr(stats, "SessionLocal", session_factory)

    result = await stats.get_day_stats(1, date=today)
    assert result is not None
    assert result.sugar == pytest.approx(6.0)
    assert result.breadUnits == pytest.approx(3.0)
    assert result.insulin == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_get_day_stats_tz_ahead(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    now = datetime.datetime(2024, 1, 1, 23, 0, tzinfo=datetime.timezone.utc)

    class DummyDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz: datetime.tzinfo | None = None) -> "DummyDatetime":
            if tz is None:
                return cast("DummyDatetime", now.replace(tzinfo=None))
            return cast("DummyDatetime", now.astimezone(tz))

    monkeypatch.setattr(stats.datetime, "datetime", DummyDatetime)

    tz = ZoneInfo("Europe/Moscow")
    day = now.astimezone(tz).date()

    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(
            Entry(
                telegram_id=1,
                event_time=datetime.datetime.combine(
                    day, datetime.time(8, 0), tzinfo=datetime.timezone.utc
                ),
                sugar_before=5.0,
                xe=1.0,
                dose=2.0,
            )
        )
        session.commit()

    monkeypatch.setattr(stats, "SessionLocal", session_factory)

    result = await stats.get_day_stats(1, tz=tz)
    assert result is not None
    assert result.sugar == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_get_day_stats_tz_behind(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    now = datetime.datetime(2024, 1, 2, 1, 0, tzinfo=datetime.timezone.utc)

    class DummyDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz: datetime.tzinfo | None = None) -> "DummyDatetime":
            if tz is None:
                return cast("DummyDatetime", now.replace(tzinfo=None))
            return cast("DummyDatetime", now.astimezone(tz))

    monkeypatch.setattr(stats.datetime, "datetime", DummyDatetime)

    tz = ZoneInfo("America/New_York")
    day = now.astimezone(tz).date()

    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(
            Entry(
                telegram_id=1,
                event_time=datetime.datetime.combine(
                    day, datetime.time(8, 0), tzinfo=datetime.timezone.utc
                ),
                sugar_before=5.0,
                xe=1.0,
                dose=2.0,
            )
        )
        session.commit()

    monkeypatch.setattr(stats, "SessionLocal", session_factory)

    result = await stats.get_day_stats(1, tz=tz)
    assert result is not None
    assert result.sugar == pytest.approx(5.0)
