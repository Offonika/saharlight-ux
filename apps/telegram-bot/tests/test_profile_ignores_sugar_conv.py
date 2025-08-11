import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import diabetes.openai_utils as openai_utils  # noqa: F401
from diabetes import dose_handlers, profile_handlers
from diabetes.db import Base, Entry, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DummyMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_profile_input_not_logged_as_sugar(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(profile_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(dose_handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    # Start sugar conversation
    sugar_msg = DummyMessage("/sugar")
    sugar_update = SimpleNamespace(
        message=sugar_msg,
        effective_user=SimpleNamespace(id=1),
        effective_chat=SimpleNamespace(id=1),
    )
    shared_chat_data: dict = {}
    sugar_context = SimpleNamespace(user_data={}, chat_data=shared_chat_data)
    await dose_handlers.sugar_start(sugar_update, sugar_context)

    # Start profile conversation which should cancel sugar conversation
    prof_msg = DummyMessage("/profile")
    prof_update = SimpleNamespace(
        message=prof_msg,
        effective_user=SimpleNamespace(id=1),
        effective_chat=SimpleNamespace(id=1),
    )
    prof_context = SimpleNamespace(args=[], user_data={}, chat_data=shared_chat_data)
    result = await profile_handlers.profile_command(prof_update, prof_context)
    assert result == profile_handlers.PROFILE_ICR
    assert "ИКХ" in prof_msg.replies[0]
    assert "sugar_active" not in shared_chat_data

    # Send ICR value
    icr_msg = DummyMessage("10")
    icr_update = SimpleNamespace(
        message=icr_msg,
        effective_user=SimpleNamespace(id=1),
        effective_chat=SimpleNamespace(id=1),
    )
    icr_context = SimpleNamespace(user_data={}, chat_data=shared_chat_data)
    result_icr = await profile_handlers.profile_icr(icr_update, icr_context)
    assert result_icr == profile_handlers.PROFILE_CF
    assert "КЧ" in icr_msg.replies[0]

    # Ensure no sugar entry was written
    with TestSession() as session:
        assert session.query(Entry).count() == 0
