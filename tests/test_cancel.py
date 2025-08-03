import os
import sys
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

# Ensure required env vars so modules import without error
os.environ.setdefault("TELEGRAM_TOKEN", "x")
os.environ.setdefault("OPENAI_API_KEY", "x")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "x")

# Make stub packages importable before importing handlers
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stubs')))

from bot.handlers import cancel_handler, menu_keyboard
from telegram.ext import ConversationHandler

@pytest.mark.asyncio
async def test_cancel_handler_shows_menu():
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data={})

    result = await cancel_handler(update, context)

    message.reply_text.assert_called_once_with(
        "❌ Действие отменено.", reply_markup=menu_keyboard
    )
    assert result == ConversationHandler.END
