from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, call

import pytest
from telegram.ext import ContextTypes

from tests.context_stub import AlertContext, ContextStub
import services.api.app.diabetes.handlers.alert_handlers as handlers


@pytest.mark.asyncio
async def test_send_alert_message_int_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When sos_contact is int, alert is sent to that chat id."""

    bot = SimpleNamespace(send_message=AsyncMock())
    context = cast(AlertContext, ContextStub(bot=bot))
    monkeypatch.setattr(
        handlers, "get_coords_and_link", AsyncMock(return_value=(None, None))
    )
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

    msg = "⚠️ У Ivan критический сахар 10.0 ммоль/л."
    assert bot.send_message.await_args_list == [
        call(chat_id=1, text=msg),
        call(chat_id=12345, text=msg),
    ]
