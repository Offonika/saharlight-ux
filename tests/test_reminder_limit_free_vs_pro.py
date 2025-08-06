from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import diabetes.reminder_handlers as handlers
from diabetes.db import Base, Reminder, User


class DummyMessage:
    def __init__(self, text: str | None = None):
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):  # pragma: no cover - kwargs unused
        self.replies.append(text)


@pytest.mark.asyncio
@pytest.mark.parametrize("plan, limit", [("free", 5), ("pro", 10)])
async def test_reminder_limit_free_vs_pro(plan, limit, monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t", plan=plan))
        for _ in range(limit):
            session.add(
                Reminder(
                    telegram_id=1,
                    type="sugar",
                    time="10:00",
                    is_enabled=True,
                )
            )
        session.commit()

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))

    state = await handlers.add_reminder_start(update, SimpleNamespace())

    assert state == handlers.ConversationHandler.END
    assert msg.replies[-1] == (
        f"У вас уже {limit} активных (лимит {plan.upper()}). Отключите одно или откройте PRO."
    )

