import asyncio
import time
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext

import pytest

from services.api.app.diabetes.handlers import reporting_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_history_view_does_not_block_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The database query is executed in a thread and doesn't block."""

    def slow_session() -> Any:
        class FakeSession:
            def __enter__(self) -> "FakeSession":
                return self

            def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
                pass

            def scalars(self, *args: Any, **kwargs: Any) -> Any:
                class Q:
                    def where(self, *a: Any, **kw: Any) -> "Q":
                        return self

                    def order_by(self, *a: Any, **kw: Any) -> "Q":
                        return self

                    def limit(self, *a: Any, **kw: Any) -> "Q":
                        return self

                    def all(self) -> list[Any]:
                        time.sleep(0.5)  # Blocking call executed in to_thread
                        return []

                return Q()

        return FakeSession()

    monkeypatch.setattr(reporting_handlers, "SessionLocal", slow_session)

    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=1),
            message=DummyMessage(),
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    flag = False

    async def marker() -> None:
        nonlocal flag
        await asyncio.sleep(0.1)
        flag = True

    view_task = asyncio.create_task(reporting_handlers.history_view(update, context))
    marker_task = asyncio.create_task(marker())

    await asyncio.wait_for(marker_task, timeout=0.2)
    await view_task
    assert flag, "Event loop was blocked during history_view"
