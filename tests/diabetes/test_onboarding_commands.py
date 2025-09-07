import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.ext import ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.bot.main as main


@pytest.mark.asyncio
async def test_finish_restores_main_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = AsyncMock()

    async def reply_text(text: str, **kwargs: object) -> None:  # noqa: ANN401
        pass

    message = SimpleNamespace(reply_text=reply_text, get_bot=lambda: bot)

    monkeypatch.setattr(onboarding.onboarding_state, "complete_state", AsyncMock())
    monkeypatch.setattr(onboarding, "_mark_user_complete", AsyncMock())
    monkeypatch.setattr(
        onboarding.reminder_handlers,
        "create_reminder_from_preset",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(onboarding, "_log_event", AsyncMock())

    result = await onboarding._finish(message, 1, {}, None)

    assert result == ConversationHandler.END
    bot.set_my_commands.assert_awaited_once_with(main.commands)
