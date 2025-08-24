import os
from unittest.mock import AsyncMock

import pytest
from telegram.ext import ApplicationBuilder, CommandHandler

import services.api.app.diabetes.handlers.registration as registration
from services.api.app.diabetes.handlers import webapp_openers


@pytest.mark.asyncio
async def test_commands_trigger_webapp_openers(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

    history = AsyncMock()
    profile = AsyncMock()
    subscription = AsyncMock()
    reminders = AsyncMock()
    monkeypatch.setattr(webapp_openers, "open_history_webapp", history)
    monkeypatch.setattr(webapp_openers, "open_profile_webapp", profile)
    monkeypatch.setattr(webapp_openers, "open_subscription_webapp", subscription)
    monkeypatch.setattr(webapp_openers, "open_reminders_webapp", reminders)
    monkeypatch.setattr(registration, "open_history_webapp", history)
    monkeypatch.setattr(registration, "open_profile_webapp", profile)
    monkeypatch.setattr(registration, "open_subscription_webapp", subscription)
    monkeypatch.setattr(registration, "open_reminders_webapp", reminders)

    app = ApplicationBuilder().token("TESTTOKEN").build()
    registration.register_handlers(app)

    handlers = [h for h in app.handlers[0] if isinstance(h, CommandHandler)]
    cmd_map = {cmd: h.callback for h in handlers for cmd in h.commands}

    await cmd_map["history"](None, None)
    await cmd_map["profile"](None, None)
    await cmd_map["subscription"](None, None)
    await cmd_map["reminders"](None, None)

    history.assert_awaited_once()
    profile.assert_awaited_once()
    subscription.assert_awaited_once()
    reminders.assert_awaited_once()
