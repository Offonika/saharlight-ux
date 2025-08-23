from types import SimpleNamespace, TracebackType
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import gpt_handlers


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

        def add(self, obj: Any) -> None:  # noqa: D401 - no action
            pass

        def commit(self) -> None:  # noqa: D401 - no action
            pass

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        return None

    monkeypatch.setattr(gpt_handlers, "run_db", None)
    monkeypatch.setattr(gpt_handlers, "SessionLocal", lambda: DummySession())
    await gpt_handlers.freeform_handler(
        update, context, commit=lambda s: True, check_alert=fake_check_alert
    )
    assert message.texts and message.texts[0].startswith("✅ Запись сохранена")
