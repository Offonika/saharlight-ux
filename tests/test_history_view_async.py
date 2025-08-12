import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.diabetes.handlers import reporting_handlers


class DummyMessage:
    async def reply_text(self, *args: Any, **kwargs: Any) -> None:
        pass


@pytest.mark.asyncio
async def test_history_view_does_not_block_event_loop(monkeypatch):
    """The database query is executed in a thread and doesn't block."""

    def slow_session():
        class FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                pass

            def query(self, *args, **kwargs):
                class Q:
                    def filter(self, *args, **kwargs):
                        return self

                    def order_by(self, *args, **kwargs):
                        return self

                    def limit(self, *args, **kwargs):
                        return self

                    def all(self):
                        time.sleep(0.5)  # Blocking call executed in to_thread
                        return []

                return Q()

        return FakeSession()

    monkeypatch.setattr(reporting_handlers, "SessionLocal", slow_session)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1),
        message=DummyMessage(),
    )
    context = SimpleNamespace()

    flag = False

    async def marker():
        nonlocal flag
        await asyncio.sleep(0.1)
        flag = True

    view_task = asyncio.create_task(reporting_handlers.history_view(update, context))
    marker_task = asyncio.create_task(marker())

    await asyncio.wait_for(marker_task, timeout=0.2)
    await view_task
    assert flag, "Event loop was blocked during history_view"
