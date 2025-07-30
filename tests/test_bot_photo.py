import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from stubs.bot_stub import photo_handler, PHOTO_SUGAR


@pytest.mark.asyncio
async def test_photo_handler_mock_mode(tmp_path):
    update = SimpleNamespace()
    photo = SimpleNamespace(file_id="id", file_unique_id="uid")
    message = SimpleNamespace(photo=[photo])
    message.reply_text = AsyncMock()
    update.message = message
    update.effective_user = SimpleNamespace(id=1)
    context = SimpleNamespace()
    context.user_data = {}
    file_mock = AsyncMock()
    file_mock.download_to_drive = AsyncMock()
    context.bot = SimpleNamespace(get_file=AsyncMock(return_value=file_mock))

    result = await photo_handler(update, context, demo=True)

    message.reply_text.assert_any_call("🔍 Анализирую фото (это займёт 5‑10 с)…")
    assert result == PHOTO_SUGAR



