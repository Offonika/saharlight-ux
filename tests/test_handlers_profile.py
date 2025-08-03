import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User


class DummyMessage:
    def __init__(self):
        self.texts = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)


@pytest.mark.parametrize(
    "args, expected_icr, expected_cf, expected_target",
    [
        (["8", "3", "6"], "8.0", "3.0", "6.0"),
        (["8,5", "3,1", "6,7"], "8.5", "3.1", "6.7"),
    ],
)
@pytest.mark.asyncio
async def test_profile_command_and_view(monkeypatch, args, expected_icr, expected_cf, expected_target):
    import os
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.openai_utils as openai_utils  # noqa: F401
    import diabetes.profile_handlers as handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=123, thread_id="t"))
        session.commit()

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(args=args, user_data={})

    await handlers.profile_command(update, context)
    assert f"ИКХ: {expected_icr} г/ед." in message.texts[0]
    assert f"КЧ: {expected_cf} ммоль/л" in message.texts[0]
    assert f"Целевой сахар: {expected_target} ммоль/л" in message.texts[0]

    message2 = DummyMessage()
    update2 = SimpleNamespace(message=message2, effective_user=SimpleNamespace(id=123))
    context2 = SimpleNamespace(user_data={})

    await handlers.profile_view(update2, context2)
    assert f"ИКХ: {expected_icr} г/ед." in message2.texts[0]
    assert f"КЧ: {expected_cf} ммоль/л" in message2.texts[0]
    assert f"Целевой сахар: {expected_target} ммоль/л" in message2.texts[0]
