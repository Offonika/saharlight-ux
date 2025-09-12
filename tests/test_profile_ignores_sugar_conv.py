import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from services.api.app.diabetes.handlers import profile as profile_handlers
import services.api.app.diabetes.services.db as db
from services.api.app.diabetes.services.db import Base, Entry, User
from tests.utils.profile_factory import make_profile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

dummy_gpt: Any = ModuleType("gpt_command_parser")
dummy_gpt.parse_command = lambda *args, **kwargs: None


class ParserTimeoutError(Exception):
    pass


dummy_gpt.ParserTimeoutError = ParserTimeoutError
sys.modules.setdefault("services.api.app.diabetes.gpt_command_parser", dummy_gpt)

dummy_main: Any = ModuleType("main")
dummy_main.BASE_DIR = Path(".")
dummy_main.UI_DIR = Path(".")
sys.modules.setdefault("services.api.app.main", dummy_main)

import services.api.app.diabetes.handlers.sugar_handlers as sugar_handlers  # noqa: E402


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_profile_input_not_logged_as_sugar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(profile_handlers, "SessionLocal", TestSession)

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        assert "sessionmaker" not in kwargs
        return await db.run_db(fn, *args, sessionmaker=TestSession, **kwargs)

    monkeypatch.setattr(sugar_handlers, "run_db", run_db_wrapper)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(make_profile(telegram_id=1))
        session.commit()

    # Start sugar conversation
    sugar_msg = DummyMessage("/sugar")
    sugar_update = cast(
        Update,
        SimpleNamespace(
            message=sugar_msg,
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(id=1),
        ),
    )
    shared_chat_data: dict[str, Any] = {}
    sugar_context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, chat_data=shared_chat_data),
    )
    await sugar_handlers.sugar_start(sugar_update, sugar_context)

    # Open profile view which should cancel sugar conversation
    prof_msg = DummyMessage("/profile")
    prof_update = cast(
        Update,
        SimpleNamespace(
            message=prof_msg,
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(id=1),
        ),
    )
    prof_context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=[], user_data={}, chat_data=shared_chat_data),
    )
    result = await profile_handlers.profile_command(prof_update, prof_context)
    assert result == profile_handlers.END
    reply = prof_msg.replies[0]
    assert "💉 *Болус*" in reply
    assert "🍽 *Углеводы*" in reply
    assert "🛡 *Безопасность*" in reply
    assert "sugar_active" not in shared_chat_data

    # Attempt to send a value; sugar conversation should be inactive
    icr_msg = DummyMessage("10")
    icr_update = cast(
        Update,
        SimpleNamespace(
            message=icr_msg,
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(id=1),
        ),
    )
    icr_context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, chat_data=shared_chat_data),
    )
    result_icr = await sugar_handlers.sugar_val(icr_update, icr_context)
    assert result_icr == sugar_handlers.END

    # Ensure no sugar entry was written
    with TestSession() as session:
        assert session.query(Entry).count() == 0
