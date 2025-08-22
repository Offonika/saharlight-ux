import pytest
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from services.api.app.diabetes.services.db import Base, User, Reminder
from services.api.app.schemas.reminders import ReminderSchema
from services.api.app.services import reminders


@pytest.fixture()
def session_factory() -> Generator[sessionmaker, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_save_and_list_reminder(monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()

    rem_id = await reminders.save_reminder(ReminderSchema(telegramId=1, type="sugar", time="08:00", orgId=42))
    assert rem_id > 0

    reminders_list = await reminders.list_reminders(1)
    assert len(reminders_list) == 1
    rem = reminders_list[0]
    assert rem.time == "08:00"
    assert rem.org_id == 42

    await reminders.save_reminder(
        ReminderSchema(
            id=rem_id,
            telegramId=1,
            type="meal",
            time="09:00",
            isEnabled=False,
        )
    )
    updated = await reminders.list_reminders(1)
    assert updated[0].type == "meal"
    assert updated[0].is_enabled is False
    assert updated[0].time == "09:00"


@pytest.mark.asyncio
@pytest.mark.parametrize("rem_id, telegram_id", [(999, 1), (1, 2)])
async def test_save_reminder_not_found_or_wrong_user(
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker,
    rem_id: int,
    telegram_id: int,
) -> None:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar"))
        session.commit()

    schema = ReminderSchema(id=rem_id, telegramId=telegram_id, type="sugar")
    with pytest.raises(HTTPException):
        await reminders.save_reminder(schema)
