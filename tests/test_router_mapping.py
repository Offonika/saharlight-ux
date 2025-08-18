import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext


class DummyQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.answered = False
        self.called: list[tuple[str, dict[str, Any]]] = []

    async def answer(self) -> None:  # pragma: no cover - trivial
        self.answered = True

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover
        self.called.append((text, kwargs))


@pytest.mark.asyncio
async def test_callback_router_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.router as router

    called: list[str] = []

    async def fake_handler(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        query: DummyQuery,
        data: str,
    ) -> None:
        called.append(data)

    monkeypatch.setitem(router.callback_handlers, "confirm_entry", fake_handler)
    query = DummyQuery("confirm_entry")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await router.callback_router(update, context)

    assert called == ["confirm_entry"]
