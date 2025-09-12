from collections.abc import Generator
from datetime import datetime, time, timedelta, timezone
from typing import Any, ContextManager, cast

import pytest
from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker

from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    ReminderLog,
    SessionMaker,
    User,
)
from services.api.app.schemas.reminders import ReminderSchema
from services.api.app.services import reminders


@pytest.fixture()
def session_factory() -> Generator[SessionMaker[SASession], None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession: SessionMaker[SASession] = sessionmaker(
        bind=engine, class_=SASession, autoflush=False, autocommit=False
    )
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_save_reminder_sets_default_title(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    rem_id = await reminders.save_reminder(
        ReminderSchema(telegramId=1, type="sugar", time=time(8, 0), orgId=42)
    )
    assert rem_id > 0

    reminders_list = await reminders.list_reminders(1)
    assert len(reminders_list) == 1
    rem = reminders_list[0]
    assert rem.time == time(8, 0)
    assert rem.org_id == 42
    assert rem.title == "Morning"


@pytest.mark.asyncio
async def test_save_reminder_preserves_title_on_update(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    rem_id = await reminders.save_reminder(
        ReminderSchema(telegramId=1, type="sugar", time=time(8, 0))
    )

    await reminders.save_reminder(
        ReminderSchema(
            id=rem_id,
            telegramId=1,
            type="meal",
            time=time(9, 0),
            isEnabled=False,
        )
    )

    updated = await reminders.list_reminders(1)
    rem = updated[0]
    assert rem.type == "meal"
    assert rem.is_enabled is False
    assert rem.time == time(9, 0)
    assert rem.title == "Morning"


@pytest.mark.asyncio
async def test_save_reminder_sets_default_title_on_update_if_missing(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    await reminders.save_reminder(
        ReminderSchema(id=1, telegramId=1, type="sugar", time=time(8, 0))
    )

    reminders_list = await reminders.list_reminders(1)
    assert reminders_list[0].title == "Morning"


@pytest.mark.asyncio
async def test_save_reminder_interval_minutes(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    rem_id = await reminders.save_reminder(
        ReminderSchema(telegramId=1, type="sugar", intervalMinutes=90)
    )
    with cast(ContextManager[SASession], session_factory()) as session:
        rem = cast(Reminder | None, session.get(Reminder, rem_id))
        assert rem is not None
        assert rem.interval_minutes == 90


@pytest.mark.asyncio
async def test_save_reminder_interval_hours(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    rem_id = await reminders.save_reminder(
        ReminderSchema(telegramId=1, type="sugar", intervalHours=2)
    )
    with cast(ContextManager[SASession], session_factory()) as session:
        rem = cast(Reminder | None, session.get(Reminder, rem_id))
        assert rem is not None
        assert rem.interval_hours == 2
        assert rem.interval_minutes == 120


@pytest.mark.asyncio
@pytest.mark.parametrize("rem_id, telegram_id", [(999, 1), (1, 2)])
async def test_save_reminder_not_found_or_wrong_user(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: SessionMaker[SASession],
    rem_id: int,
    telegram_id: int,
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()

    schema = ReminderSchema(id=rem_id, telegramId=telegram_id, type="sugar")
    with pytest.raises(HTTPException):
        await reminders.save_reminder(schema)


@pytest.mark.asyncio
async def test_save_reminder_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_run_db(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("bad data")

    monkeypatch.setattr(reminders, "run_db", fail_run_db)

    with pytest.raises(HTTPException) as exc:
        await reminders.save_reminder(ReminderSchema(telegramId=1, type="sugar"))

    assert exc.value.status_code == 422
    assert exc.value.detail == "bad data"


@pytest.mark.asyncio
async def test_save_reminder_missing_id(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    original_refresh = SASession.refresh

    def fake_refresh(self: SASession, instance: Any, *args: Any, **kwargs: Any) -> None:
        original_refresh(self, instance, *args, **kwargs)
        instance.id = None

    monkeypatch.setattr(SASession, "refresh", fake_refresh)

    with pytest.raises(HTTPException) as exc:
        await reminders.save_reminder(ReminderSchema(telegramId=1, type="sugar"))

    assert exc.value.status_code == 500
    assert exc.value.detail == "reminder id missing after commit"


@pytest.mark.asyncio
async def test_list_reminders_invalid_user(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    reminders_list = await reminders.list_reminders(999)
    assert reminders_list == []


@pytest.mark.asyncio
async def test_list_reminders_stats(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    now = datetime.now(timezone.utc)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        recent = now - timedelta(days=1)
        session.add(ReminderLog(reminder_id=1, telegram_id=1, event_time=recent))
        session.add(
            ReminderLog(
                reminder_id=1, telegram_id=1, event_time=now - timedelta(days=8)
            )
        )
        session.commit()
    reminders_list = await reminders.list_reminders(1)
    assert getattr(reminders_list[0], "fires7d") == 1
    last = getattr(reminders_list[0], "last_fired_at")
    assert last is not None
    assert last.replace(tzinfo=None, microsecond=0) == recent.replace(
        tzinfo=None, microsecond=0
    )


@pytest.mark.asyncio
async def test_save_reminder_kind_and_days(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    rem_id = await reminders.save_reminder(
        ReminderSchema(
            telegramId=1,
            type="sugar",
            kind="at_time",
            time=time(8, 0),
            daysOfWeek=[1, 3, 5],
        )
    )
    with cast(ContextManager[SASession], session_factory()) as session:
        rem = cast(Reminder | None, session.get(Reminder, rem_id))
        assert rem is not None
        assert rem.kind == "at_time"
        assert rem.daysOfWeek == [1, 3, 5]


@pytest.mark.asyncio
async def test_list_reminders_next_at(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    monkeypatch.setattr(
        reminders,
        "compute_next",
        lambda rem, tz: datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()
    rems = await reminders.list_reminders(1)
    assert getattr(rems[0], "next_at") == datetime(2023, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_delete_reminder(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()

    await reminders.delete_reminder(1, 1)
    with cast(ContextManager[SASession], session_factory()) as session:
        assert cast(Any, session).get(Reminder, 1) is None


@pytest.mark.asyncio
async def test_delete_reminder_with_logs(
    monkeypatch: pytest.MonkeyPatch, session_factory: SessionMaker[SASession]
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.add(ReminderLog(reminder_id=1, telegram_id=1))
        session.commit()

    await reminders.delete_reminder(1, 1)
    with cast(ContextManager[SASession], session_factory()) as session:
        assert cast(Any, session).get(Reminder, 1) is None
        logs = session.query(ReminderLog).all()
        assert len(logs) == 1
        assert logs[0].reminder_id is None


@pytest.mark.asyncio
@pytest.mark.parametrize("rid, tid", [(999, 1), (1, 2)])
async def test_delete_reminder_not_found_or_wrong_user(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: SessionMaker[SASession],
    rid: int,
    tid: int,
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with cast(ContextManager[SASession], session_factory()) as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()
    with pytest.raises(HTTPException):
        await reminders.delete_reminder(tid, rid)
