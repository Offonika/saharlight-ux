import json
from datetime import time
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    SubscriptionPlan,
    User,
)


class DummyMessage:
    def __init__(self) -> None:
        self.web_app_data: SimpleNamespace = SimpleNamespace()
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - kwargs unused
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plan, limit",
    [
        (SubscriptionPlan.FREE, 5),
        (SubscriptionPlan.PRO, 10),
        (SubscriptionPlan.FAMILY, 20),
    ],
)
async def test_reminder_limit_by_plan(
    plan: SubscriptionPlan, limit: int, monkeypatch: pytest.MonkeyPatch
) -> None:
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
                    time=time(10, 0),
                    is_enabled=True,
                )
            )
        session.commit()

    msg = DummyMessage()
    msg.web_app_data.data = json.dumps({"type": "sugar", "value": "09:00"})
    update: Any = SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context: Any = SimpleNamespace(
        job_queue=SimpleNamespace(
            run_daily=lambda *a, **k: None,
            run_repeating=lambda *a, **k: None,
            get_jobs_by_name=lambda name: [],
        )
    )

    await handlers.reminder_webapp_save(update, context)

    assert msg.replies[-1] == (
        f"У вас уже {limit} активных (лимит {plan.value.upper()}). Отключите одно или откройте PRO."
    )
