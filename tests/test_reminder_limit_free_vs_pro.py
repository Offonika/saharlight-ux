import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Reminder
import diabetes.reminder_handlers as handlers


class DummyMessage:
    def __init__(self, text: str | None = None):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


@pytest.mark.asyncio
async def test_reminder_limit_free_vs_pro():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession

    # Free plan user with 5 active reminders and one disabled
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t1", plan="free"))
        for _ in range(5):
            session.add(
                Reminder(
                    telegram_id=1,
                    type="sugar",
                    time="10:00",
                    is_enabled=True,
                )
            )
        session.add(
            Reminder(
                telegram_id=1,
                type="sugar",
                time="10:00",
                is_enabled=False,
            )
        )
        session.commit()

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    state = await handlers.add_reminder_start(update, SimpleNamespace())
    assert state == handlers.ConversationHandler.END
    assert msg.replies[-1] == (
        "У вас уже 5 активных (лимит FREE). Отключите одно или откройте PRO."
    )

    # Pro plan user with 10 active reminders
    with TestSession() as session:
        session.add(User(telegram_id=2, thread_id="t2", plan="pro"))
        for _ in range(10):
            session.add(
                Reminder(
                    telegram_id=2,
                    type="sugar",
                    time="10:00",
                    is_enabled=True,
                )
            )
        session.commit()

    msg2 = DummyMessage()
    update2 = SimpleNamespace(message=msg2, effective_user=SimpleNamespace(id=2))
    state2 = await handlers.add_reminder_start(update2, SimpleNamespace())
    assert state2 == handlers.ConversationHandler.END
    assert msg2.replies[-1] == (
        "У вас уже 10 активных (лимит PRO). Отключите одно или откройте PRO."
    )
