from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from telegram.ext import ContextTypes

from tests.context_stub import AlertContext, ContextStub
import services.api.app.diabetes.handlers.alert_handlers as handlers


async def fake_get_coords_and_link() -> tuple[str | None, str | None]:
    """Return empty coordinates for tests."""
    return None, None


@pytest.mark.asyncio
async def test_send_alert_message_int_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Numeric SOS contact triggers message sending."""

    bot = SimpleNamespace(send_message=AsyncMock())
    context = cast(AlertContext, ContextStub(bot=bot))
    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    profile: dict[str, Any] = {
        "sos_contact": 12345,
        "sos_alerts_enabled": True,
    }

    await handlers._send_alert_message(
        1,
        10.0,
        profile,
        cast(ContextTypes.DEFAULT_TYPE, context),
        "Ivan",
    )

    assert bot.send_message.await_count == 2
    assert bot.send_message.await_args_list[1].kwargs["chat_id"] == 12345


__all__ = ["test_send_alert_message_int_contact"]

