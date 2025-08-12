import json
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.services.db import Base, Reminder, User


class DummyMessage:
    def __init__(self):
        self.web_app_data = SimpleNamespace()
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - kwargs unused
        self.replies.append(text)


@pytest.mark.asyncio
@pytest.mark.parametrize("plan, limit", [("free", 5), ("pro", 10)])
async def test_reminder_limit_free_vs_pro(plan, limit, monkeypatch) -> None:
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
    msg.web_app_data.data = json.dumps({"type": "sugar", "value": "09:00"})
    update = SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=SimpleNamespace(run_daily=lambda *a, **k: None, run_repeating=lambda *a, **k: None, get_jobs_by_name=lambda name: []))

    await handlers.reminder_webapp_save(update, context)

    assert msg.replies[-1] == (
        f"У вас уже {limit} активных (лимит {plan.upper()}). Отключите одно или откройте PRO."
    )

