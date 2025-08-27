from types import SimpleNamespace, TracebackType
from typing import Any, Callable, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import gpt_handlers
from sqlalchemy.orm import Session


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_freeform_handler_db_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("5")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}, "pending_fields": ["sugar"]}),
    )
    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        def add(self, obj: Any) -> None:
            pass

    def session_factory() -> Session:
        return cast(Session, DummySession())

    def failing_commit(session: Session) -> None:
        raise AttributeError("db failure")

    monkeypatch.setattr(gpt_handlers, "run_db", None)
    monkeypatch.setattr(gpt_handlers, "SessionLocal", session_factory)

    with pytest.raises(AttributeError):
        await gpt_handlers.freeform_handler(
            update, context, commit=cast(Callable[[Session], None], failing_commit)
        )
