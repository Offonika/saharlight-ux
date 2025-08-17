from types import SimpleNamespace
from typing import Any, cast

import builtins
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.services.db import Base, User


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.markups: list[Any] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - simple helper
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)

    async def delete(self) -> None:  # pragma: no cover - simple helper
        pass


@pytest.mark.asyncio
async def test_profile_command_and_view_without_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Profile commands should work even when ``diabetes_sdk`` is missing."""

    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: Any = None,
        locals: Any = None,
        fromlist: Any = (),
        level: int = 0,
    ) -> Any:
        if name.startswith("diabetes_sdk"):
            raise ImportError("diabetes_sdk not available")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

    from services.api.app.diabetes.handlers import profile as handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=123, thread_id="t"))
        session.commit()

    msg = DummyMessage()
    update = cast(Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=123)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=["8", "3", "6", "4", "9"], user_data={}),
    )

    await handlers.profile_command(update, context)
    assert msg.texts and "ИКХ: 8.0 г/ед." in msg.texts[0]

    msg2 = DummyMessage()
    update2 = cast(Update, SimpleNamespace(message=msg2, effective_user=SimpleNamespace(id=123)))
    context2 = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await handlers.profile_view(update2, context2)
    assert msg2.texts and "ИКХ: 8.0 г/ед." in msg2.texts[0]
